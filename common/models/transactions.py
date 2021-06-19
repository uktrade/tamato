"""Transaction model and manager."""
from __future__ import annotations

import json
from typing import Iterator

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.aggregates import Count
from django.db.models.expressions import Window
from django.db.models.functions.window import RowNumber
from django_cte import CTEManager
from django_cte import With
from django_cte.cte import CTEQuerySet

from common.xml.sql import XMLSerialize
from common.business_rules import BusinessRuleChecker
from common.business_rules import BusinessRuleViolation
from common.models.mixins import TimestampedMixin
from common.models.records import TrackedModel


class TransactionManager(CTEManager):
    """Sorts TrackedModels by record_number and subrecord_number."""

    def get_queryset(self):
        annotate_record_code = self.model.tracked_models.rel.related_model.objects
        return TransactionQueryset(self.model, using=self._db).prefetch_related(
            models.Prefetch("tracked_models", queryset=annotate_record_code),
        )


class TransactionQueryset(CTEQuerySet):
    def ordered_tracked_models(self):
        """TrackedModel in order of their transactions creation order."""

        tracked_models = self.model.tracked_models.rel.related_model.objects.filter(
            transaction__in=self,
        ).order_by(
            "transaction__order",
        )  # order_by record_code, subrecord_code already happened in get_queryset
        return tracked_models

    def with_xml(self):
        from importer.taric import TransactionParser

        assert any(
            self.query.where.children,
        ), """TransactionQuerySet.with_xml was called on an unfiltered queryset.
        This will result in a very slow query that generates XML for all
        database models. Instead of filtering the queryset after the call, you
        need to filter the Transaction queryset before calling with_xml()."""

        # The "message id" field is a sequential number unique per envelope
        # (e.g. each envelope starts a new sequence). That behaviour can be
        # achieved by using a window function in SQL, but to do that all of the
        # models need to be generated up front and together (rather than in
        # separate subqueries). So first a CTE is of all the models is used.
        #
        # Note that this means the caller needs to be very careful about
        # filtering: if the list of transactions is not filtered before the call
        # to `with_xml()`, this will result in the DB trying to generate XML for
        # _all_ of the TrackedModels. So transactions need to be filtered first.
        models = With(
            TrackedModel.objects.all()
            .annotate(message_id=Window(expression=RowNumber()))
            .filter(transaction__in=self),
            name="models",
        )

        # Django is too clever with expressions – any annotation is knows about
        # it tries to substitute in any place it is referenced. This doesn't
        # work here because it results in the window function being substituted
        # inside the subquery, which defeats the point. So instead 2 levels of
        # CTEs need to be used – the first above, and the second to actually
        # generate the XML.
        xml_models = With(
            models.join(TrackedModel, pk=models.col.pk)
            .annotate(message_id=models.col.message_id)
            .with_xml(),
            name="xml_models",
        )

        return (
            xml_models.join(self, pk=xml_models.col.transaction_id)
            .with_cte(models)
            .with_cte(xml_models)
            .annotate(
                xml=XMLSerialize(
                    TransactionParser().serializer(xml_models.col.xml),
                ),
            )
        )

    def not_empty(self):
        # Django bug 2361  https://code.djangoproject.com/ticket/2361
        #   Queryset.filter(m2mfield__isnull=False) may duplicate records,
        #   so cannot be used, instead the count() of each tracked_models
        #   resultset is checked.
        full_transactions = self.annotate(models=Count("tracked_models")).filter(
            models__gt=0,
        )
        return self.filter(pk__in=full_transactions)

    def get_xml(self) -> Iterator[str]:
        return (
            self.with_xml()
            .values_list("xml", flat=True)
            .iterator(
                chunk_size=settings.EXPORTER_MAXIMUM_DATABASE_CHUNK,
            )
        )


class Transaction(TimestampedMixin):
    """
    Contains a group of one or more TrackedModel instances that must be applied
    atomically.

    Linked to a WorkBasket and may be contained by one or more Envelopes when exported.

    Business rule validation is performed at Transaction level for creates, updates and
    deletes. Business rules are also validated at the TrackedModel level for creates.
    """

    import_transaction_id = models.IntegerField(null=True, editable=False)
    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    # The order this transaction appears within the workbasket
    order = models.IntegerField()

    composite_key = models.CharField(max_length=16, unique=True)

    objects = TransactionManager.from_queryset(TransactionQueryset)()

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

    def add_to_transaction(self, instance, **kwargs):
        if hasattr(instance, "transaction"):
            instance.transaction = self

    @classmethod
    def latest_approved(cls) -> Transaction:
        """Returns the transaction most recently committed to the global stream
        of approved transactions."""
        WorkBasket = cls._meta.get_field("workbasket").related_model
        WorkflowStatus = type(WorkBasket._meta.get_field("status").default)
        return (
            cls.objects.exclude(
                workbasket=WorkBasket.objects.first(),
            )
            .filter(
                workbasket__status__in=WorkflowStatus.approved_statuses(),
            )
            .order_by("order")
            .last()
        )


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
