"""Transaction model and manager."""
from __future__ import annotations

import json
from logging import getLogger

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.transaction import atomic
from django_fsm import FSMIntegerField
from django_fsm import transition

from common.business_rules import BusinessRuleChecker
from common.business_rules import BusinessRuleViolation
from common.models.mixins import TimestampedMixin
from common.renderers import counter_generator

logger = getLogger(__name__)
PREEMPTIVE_TRANSACTION_SEED = -100000


class TransactionPartition(models.IntegerChoices):
    """
    Transactions are partitioned into global groupings based on type.

    Within a partition, a transactions order applies, to obtain a global
    ordering a order_by("partition", "order") must be used.
    """

    SEED_FILE = 1, "Seed"
    REVISION = 2, "Revision"
    DRAFT = 3, "Draft"

    @classmethod
    def approved_partitions(cls):
        return [cls.SEED_FILE, cls.REVISION]


class TransactionManager(models.Manager):
    """Sorts TrackedModels by record_number and subrecord_number."""

    def get_queryset(self):
        annotate_record_code = self.model.tracked_models.rel.related_model.objects.annotate_record_codes().order_by(
            "record_code",
            "subrecord_code",
        )
        return (
            super()
            .get_queryset()
            .prefetch_related(
                models.Prefetch("tracked_models", queryset=annotate_record_code),
            )
        )


class ApprovedTransactionManager(TransactionManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(partition__in=TransactionPartition.approved_partitions())
        )


class TransactionsAlreadyApproved(Exception):
    pass


class TransactionQueryset(models.QuerySet):
    def unordered_tracked_models(self):
        """Usually 'ordered_tracked_models' is required."""
        return self.model.tracked_models.rel.related_model.objects.filter(
            transaction__in=self,
        )

    def ordered_tracked_models(self):
        """TrackedModel in order of their transactions creation order."""

        tracked_models = self.unordered_tracked_models().order_by(
            "transaction__partition",
            "transaction__order",
        )  # order_by record_code, subrecord_code already happened in get_queryset
        return tracked_models

    def approved(self):
        """
        Currently approved Transactions are SEED_FILE and REVISION this can be
        more efficiently expressed as != DRAFT.

        Using exclude(DRAFT) should be marginally more efficient than
        filter(partition__in=TransactionPartition.approved_partitions())
        """
        return self.exclude(partition=TransactionPartition.DRAFT)

    @atomic
    def apply_transaction_order(self, partition_scheme) -> None:
        """
        Reorder transactions in the workbasket.

        Note that transaction orders may not be contiguous,
        e.g. when the workbasket has preemptive transactions
        (created by the commodity code change handler).

        TODO: Enhance this method to order based on partitions also.
        """
        first_tx = self.order_by("order").first()

        if self.order_by("order").first().order < 0:
            pass
        else:
            first_tx.order

        # Ensure order of the transactions in this query to start at the end of the existing approved partition.
        existing_tx = self.model.objects.filter(
            partition=partition_scheme.get_approved_partition(),
        ).last()
        order_start = existing_tx.order + 1 if existing_tx else 0

        counter = counter_generator(start=order_start + 1)

        logger.debug(
            "Update draft transactions in query starting from %s "
            "to start after transaction %s. order_start: %s",
            first_tx.pk,
            existing_tx.pk if existing_tx else None,
            order_start,
        )

        for tx in self.order_by("order").all():
            tx.order = counter()
            tx.save()

    @atomic
    def save_drafts(self, partition_scheme):
        """
        Save draft transactions as either SEED_FILE or REVISION transactions.

        Contained tracked models to become the current version. Order field is
        updated so these transactions are at the end of the approved partition
        """
        if self.approved().exists():
            pks = self.values_list("pk")
            msg = f"One or more Transactions was not in the DRAFT partition: {pks}"
            logger.error(msg)
            raise TransactionsAlreadyApproved(msg)

        if self.first() is None:
            logger.info("Draft contains no transactions, bailing out early.")
            return

        # Find the transaction in the destination approved partition with the highest order
        # get_approved_partition may raise a ValueError, e.g. when attempting to create
        # a seed transaction when revisions exist, so it is called before any of the
        # later queries.
        logger.info("Save drafts with partition scheme %s", repr(partition_scheme))
        approved_partition = partition_scheme.get_approved_partition()

        logger.debug(
            "Approved partition %s selected by partition_scheme.",
            approved_partition,
        )
        logger.debug("Update versions_group.")

        for obj in self.unordered_tracked_models().order_by("pk"):
            version_group = obj.version_group
            version_group.current_version = obj
            version_group.save()

        self.apply_transaction_order(partition_scheme)
        self.update(partition=approved_partition)


class Transaction(TimestampedMixin):
    """
    Contains a group of one or more TrackedModel instances that must be applied
    atomically.

    Linked to a WorkBasket and may be contained by one or more Envelopes when exported.

    Business rule validation is performed at Transaction level for creates, updates and
    deletes. Business rules are also validated at the TrackedModel level for creates.

    Mutation rules:

    Only transactions in the DRAFT partition should be modified - at that point they may be
    moved to SEED_FILE or REVISION partitions, and the order field will be updated.

    Transactions in SEED_FILE or REVISION partitions should not be modified.
    """

    class Meta:
        # See TransactionPartition for information on workbasket_status order.
        ordering = ("partition", "order")

    # FSMField protects against unexpected state changes.
    partition = FSMIntegerField(
        default=TransactionPartition.DRAFT.value,
        choices=TransactionPartition.choices,
        db_index=True,
        protected=False,
    )

    import_transaction_id = models.IntegerField(null=True, editable=False)
    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    # Order of transaction within its partition.
    # The default order ("partition", "order") gives global ordering.
    order = models.IntegerField()

    composite_key = models.CharField(max_length=16, unique=True)

    objects = TransactionManager.from_queryset(TransactionQueryset)()

    approved = ApprovedTransactionManager.from_queryset(TransactionQueryset)()

    @transition(
        field=partition,
        source=TransactionPartition.DRAFT,
        target=TransactionPartition.REVISION,
    )
    def save_draft(self, partition_scheme):
        """
        Finalise a single DRAFT transaction as a REVISION.

        Delegates to Transaction.objects.save_drafts() which is a better choice
        if updating many records.
        """
        type(self).objects.filter(pk=self.pk).save_drafts(partition_scheme)
        self.refresh_from_db()
        return self

    def clean(self):
        """Validate business rules against contained TrackedModels."""

        if settings.SKIP_VALIDATION:
            return

        self.errors = []

        try:
            BusinessRuleChecker(self.tracked_models.all(), self).validate()
        except BusinessRuleViolation as violation:
            self.errors.append(violation)

        if self.errors:
            raise ValidationError(self.errors)

    def to_json(self):
        """
        Serialize to JSON.

        Used for storing in the session.
        """

        return json.dumps(
            {key: val for key, val in self.__dict__.items() if key != "_state"},
            cls=DjangoJSONEncoder,
        )

    def __enter__(self):
        models.signals.pre_save.connect(self.add_to_transaction, dispatch_uid=id(self))
        return self

    def __exit__(self, *exc):
        models.signals.pre_save.disconnect(
            self.add_to_transaction,
            dispatch_uid=id(self),
        )

    def __repr__(self):
        return f"<Transaction pk={self.pk}, order={self.order}, partition={self.partition}>"

    def add_to_transaction(self, instance, **kwargs):
        if hasattr(instance, "transaction"):
            instance.transaction = self


class TransactionGroup(models.Model):
    """
    An ordered group of Transactions.

    Transactions often must be applied in a specific sequence, for example to ensure
    a Measure exists before a Footnote can be associated with it.

    A Transaction may belong to several groups, for example a group associated with an
    imported Envelope, and with a WorkBasket.
    """

    group_id = models.IntegerField()
    order_in_group = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT)
