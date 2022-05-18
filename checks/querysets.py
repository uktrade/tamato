from django.contrib.postgres.aggregates import BoolOr
from django.db import models
from django.db.models import expressions
from django.db.models.aggregates import Count
from django.db.models.aggregates import Max
from django_cte import CTEQuerySet
from django_cte import With

from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.utils import LazyTransaction

latest_transaction = LazyTransaction(get_value=Transaction.approved.last)


class TransactionCheckQueryset(CTEQuerySet):
    currentness_filter = (
        # If the head transaction is ahead of the latest transaction then no new
        # transactions have been committed since the check. In practice we only
        # expect the head_transaction == latest_transaction but it doesn't hurt
        # to be more defensive with a greater than check.
        #
        #    head_transaction >= latest_transaction
        models.Q(
            head_transaction__partition__gt=latest_transaction.partition,
        )
        | models.Q(
            head_transaction__partition=latest_transaction.partition,
            head_transaction__order__gte=latest_transaction.order,
        )
        # If the head transaction was ahead of the checked transaction when the
        # check was carried out, and the checked transaction is approved, we
        # don't need to update anything because subsequent changes can't affect
        # the older transaction.
        #
        #    head_transaction >= checked_transaction AND checked_transaction is
        #    approved
        | models.Q(
            head_transaction__partition__gt=models.F("transaction__partition"),
            transaction__partition__in=TransactionPartition.approved_partitions(),
        )
        | models.Q(
            head_transaction__partition=models.F("transaction__partition"),
            head_transaction__order__gte=models.F("transaction__order"),
            transaction__partition__in=TransactionPartition.approved_partitions(),
        )
    )

    freshness_fields = {
        # See the field descriptions on ``TransactionCheck`` for details on
        # how these fields are populated and used to calculate freshness.
        "tracked_model_count": Count("transaction__tracked_models"),
        "latest_tracked_model": Max("transaction__tracked_models__id"),
    }

    freshness_annotations = {
        f"real_{field}": expr for field, expr in freshness_fields.items()
    }

    freshness_filter = (
        # Use the metadata on the transaction check to work out if the check
        # still represents the data in the transaction. The "real_" fields are
        # expected to be annotated onto the queryset and represent the current
        # state of the transaction.
        #
        # A fresh check is where all the current values match the stored values.
        models.Q(**{field: models.F(f"real_{field}") for field in freshness_fields})
        # ...or where there are no models to check, which is valid.
        | models.Q(
            real_latest_tracked_model__isnull=True,
            latest_tracked_model__isnull=True,
        )
    )

    requires_update_filter = (~freshness_filter) | (~currentness_filter)

    requires_update_annotation = expressions.ExpressionWrapper(
        expression=requires_update_filter,
        output_field=models.fields.BooleanField(),
    )

    def current(self):
        """
        A ``TransactionCheck`` is considered "current" if there hasn't been any
        data added after the check that could change the result of the check.

        If the checked transaction is in a draft partition, "current" means no
        new transactions have been approved since the check was carried out. If
        any have, they will now potentially be in scope of the check.

        If the checked transaction is in an approved partition, "current" means
        no transactions were approved between the check happening and the
        transaction being committed to the approved partition (but some may have
        been added after it, which can't affect its result).
        """
        return self.filter(self.currentness_filter)

    def fresh(self):
        """
        A ``TransactionCheck`` is considered "fresh" if the transaction that it
        checked hasn't been modified since the check was carried out, which
        could change the result of the check.

        The ``tracked_model_count`` and ``latest_tracked_model`` of the checked
        transaction are cached on the check and used to detect this.
        """
        return self.annotate(**self.freshness_annotations).filter(self.freshness_filter)

    def stale(self):
        """A ``TransactionCheck`` is considered "stale" if the transaction that
        it checked has been modified since the check was carried out, which
        could change the result of the check."""
        return self.annotate(**self.freshness_annotations).exclude(
            self.freshness_filter,
        )

    def requires_update(self, requirement=True, include_archived=False):
        """
        A ``TransactionCheck`` requires an update if it or any check on a
        transaction before it in order is stale or no longer current.

        If a ``TransactionCheck`` on an earlier transaction is stale, it means
        that transaction has been modified since the check was done, which could
        also invalidate any checks of any subsequent transactions.

        By default transactions in ARCHIVED workbaskets are ignored, since these
        workbaskets exist outside of the normal workflow.
        """

        if include_archived:
            ignore_filter = {}
        else:
            ignore_filter = {"transaction__workbasket__status": "ARCHIVED"}

        # First filtering out any objects we should ignore,
        # work out for each check whether it alone requires an update, by
        # seeing whether it is stale or not current.
        basic_info = With(
            self.model.objects.exclude(**ignore_filter)
            .annotate(**self.freshness_annotations)
            .annotate(
                requires_update=self.requires_update_annotation,
            ),
            name="basic_info",
        )

        # Now cascade that result down to any subsequent transactions: if a
        # transaction in the same workbasket comes later, then it will also
        # require an update. TODO: do stale transactions pollute the update
        # check for ever?
        sequence_info = With(
            basic_info.join(self.model.objects.all(), pk=basic_info.col.pk).annotate(
                requires_update=expressions.Window(
                    expression=BoolOr(basic_info.col.requires_update),
                    partition_by=models.F("transaction__workbasket"),
                    order_by=[
                        models.F("transaction__order").asc(),
                        models.F("pk").desc(),
                    ],
                ),
            ),
            name="sequence_info",
        )

        # Now filter for only the type that we want: checks that either do or do
        # not require an update.
        return (
            sequence_info.join(self, pk=sequence_info.col.pk)
            .with_cte(basic_info)
            .with_cte(sequence_info)
            .annotate(requires_update=sequence_info.col.requires_update)
            .filter(requires_update=requirement)
        )
