"""Transaction model and manager."""
from __future__ import annotations

import json
from logging import getLogger

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.transaction import atomic
from django_fsm import FSMIntegerField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from common.models.utils import lazy_string
from common.renderers import counter_generator

logger = getLogger(__name__)
PREEMPTIVE_TRANSACTION_SEED = -100000


class TransactionPartition(models.IntegerChoices):
    """
    Transactions are partitioned into global groupings based on type.

    Within a partition, a transactions order applies, to obtain a global
    ordering call .order_by("partition", "order").

    The numbers chosen increment by "era" of transaction, starting
    from approved transactions SEED_FILE, REVISION
    then ending with DRAFT.

    This system enables a simple filter for "approved" transactions, by checking
    for <= HIGHEST_APPROVED_PARTITION, this is currently set to REVISION,
    which is implemented in TransactionQuerySet.approved().
    """

    SEED_FILE = 1, "Seed"
    REVISION = 2, "Revision"
    DRAFT = 3, "Draft"

    @classmethod
    def get_highest_approved_partition(cls):
        """Return the highest approved partition, this is used by
        TransactionQuerySet.approved() to filter approved partitions using a
        comparison operator as opposed to "in"."""
        # This is a function, not a const as duplicate are not allowed in an Enum.
        return cls.REVISION

    @classmethod
    def approved_partitions(cls):
        return [cls.SEED_FILE, cls.REVISION]


class TransactionManager(models.Manager):
    pass


class ApprovedTransactionManager(TransactionManager):
    def get_queryset(self):
        return super().get_queryset().approved()


class TransactionsAlreadyApproved(Exception):
    pass


class TransactionsAlreadyInDraft(Exception):
    pass


class TransactionQueryset(models.QuerySet):
    @property
    def tracked_models(self):
        """Returns all tracked models referenced by transactions in this
        queryset."""
        return self.model.tracked_models.rel.related_model.objects.filter(
            transaction__in=self,
        )

    def approved(self):
        """Currently approved Transactions are SEED_FILE and REVISION this can
        be."""
        return self.filter(
            partition__lte=TransactionPartition.get_highest_approved_partition(),
        )

    def unapproved(self):
        return self.exclude(
            partition__lte=TransactionPartition.get_highest_approved_partition(),
        )

    def preorder_negative_transactions(self) -> None:
        """
        Makes all order numbers negative if there is even one negative order
        number.

        Negative order numbers happen in preemptive transactions, e.g. when we
        import commodity code changes
        """
        if self.count() and self.order_by("order").first().order < 0:
            order = PREEMPTIVE_TRANSACTION_SEED
            transactions = self.order_by("order")
            for tx in transactions:
                order += 1
                tx.order = order

            type(self).objects.bulk_update(transactions, ["order"])

    @atomic
    def move_to_end_of_partition(self, partition) -> None:
        """
        Update Transaction partition and order fields to place them at the end
        of the specified partition.

        Transaction order is updated to be contiguous.
        """

        transactions = self.order_by("partition", "order")

        # Ensure order of the transactions in this query to start at end of the partition.
        # The order_by here is redundant - as it's the natural order of Transaction,
        # but it's included for clarity.
        existing_tx = (
            self.model.objects.order_by("order")
            .filter(
                partition=partition,
            )
            .exclude(pk__in=transactions.values_list("pk", flat=True))
            .last()
        )
        order_start = existing_tx.order + 1 if existing_tx else 1

        logger.debug(
            "Update transactions in query starting from %s "
            "to start after transaction %s. order_start: %s",
            transactions.first().pk,
            existing_tx.pk if existing_tx else None,
            order_start,
        )

        counter = counter_generator(start=order_start)

        for tx in transactions:
            tx.order = counter()
            tx.partition = partition

        self.model.objects.bulk_update(transactions, ["partition", "order"])

    @atomic
    def save_drafts(self, partition_scheme):
        """
        Save draft transactions as either SEED_FILE or REVISION transactions.

        Contained tracked models to become the current version. Order field is
        updated so these transactions are at the end of the approved partition
        """
        if self.exists():
            logger.info("Draft contains no transactions, bailing out early.")
            return

        if self.approved().exists():
            pks = self.values_list("pk")
            msg = f"One or more Transactions was not in the DRAFT partition: {pks}"
            logger.error(msg)
            raise TransactionsAlreadyApproved(msg)

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
        logger.debug("Update version_group.")

        for obj in self.tracked_models.order_by("pk"):
            version_group = obj.version_group
            version_group.current_version = obj
            version_group.save()

        self.move_to_end_of_partition(approved_partition)

    @atomic
    def revert_current_version(self):
        """Set current_version to previous version or None on a basket's tracked
        model version groups."""
        for obj in self.tracked_models.order_by("-pk").select_related("version_group"):
            version_group = obj.version_group
            versions = (
                version_group.versions.has_approved_state()
                .order_by("-pk")
                .exclude(pk=obj.pk)
            )
            if versions.count() == 0:
                version_group.current_version = None
            else:
                version_group.current_version = versions.first()
            version_group.save()

    @atomic
    def move_to_draft(self):
        """
        Save SEED_FILE or REVISION transactions as DRAFT.

        Set current_version to previous version or None on a basket's tracked
        model version groups.
        """
        if self.exists():
            logger.info("Queryset contains no transactions, bailing out early.")
            return

        if self.unapproved().exists():
            pks = self.values_list("pk")
            msg = f"One or more Transactions was already in the DRAFT partition: {pks}"
            logger.error(msg)
            raise TransactionsAlreadyInDraft(msg)

        logger.debug("Update version_group.")

        self.revert_current_version()

        logger.info("Save with DRAFT partition scheme")

        self.move_to_end_of_partition(TransactionPartition.DRAFT)


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
        indexes = (models.Index(fields=("partition", "order")),)

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

    @lazy_string
    def _get_summary(self):
        """
        Return a short summary of the transaction.

        Attempts a balance between readability and enough information to debug
        issues, so contains the pk and status of the transaction and workbasket.

        Stringification is lazily evaluated, so this property can be passed to loggers.
        """
        return (
            f"transaction: {self.partition}, {self.pk} "
            f"in workbasket: {self.workbasket.status}, {self.workbasket.pk}"
        )

    @property
    def summary(self):
        """
        Return a short summary of the transaction.

        Attempts a balance between readability and enough information to debug
        issues, so contains the partion, order for transactions and pk, status
        for workbaskets.

        Stringification happens lazily so this property is suitable for use
        when logging.
        """
        # This is not decorated with lazy_string because it doesn't work with properties
        return self._get_summary()


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
