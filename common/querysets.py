from datetime import date

from django.db.models import Q
from django.db.models import QuerySet


class ValidityQuerySet(QuerySet):
    """A mixin for querysets dealing with models that have validity periods."""

    def with_validity_field(self):
        """
        Returns a QuerySet which will have this model's validity date field (as
        specified by :attr:`validity_field_name`) present on the returned
        models.

        The need for this is that some models (e.g.
        :class:`~measures.models.Measure`) use a validity date that is computed
        on demand as part of a database query and hence is not present on the
        default queryset, and so will override this method.
        """
        return self

    def not_in_effect(self, at_date: date) -> QuerySet:
        """
        Filter queryset to only those whose validity period does NOT include the
        given date.

        :param at_date date: Exclude results whose validity period contains this date.
        :rtype QuerySet:
        """
        return self.with_validity_field().exclude(
            **{f"{self.model.validity_field_name}__contains": at_date},
        )

    def no_longer_in_effect(self, at_date: date) -> QuerySet:
        """
        Filter queryset to only those whose validity period ends before the
        given date.

        :param at_date date: Exclude results whose validity period contains or comes
        after this date.
        :rtype QuerySet:
        """
        return self.with_validity_field().filter(
            ~Q(**{f"{self.model.validity_field_name}__contains": at_date})
            & ~Q(**{f"{self.model.validity_field_name}__startswith__gt": at_date}),
        )

    def not_yet_in_effect(self, at_date: date) -> QuerySet:
        """
        Filter the queryset to only those whose validity period starts after the
        given date.

        :param at_date date: Exclude results with validity starts before this date.
        :rtype QuerySet:
        """
        return self.with_validity_field().filter(
            **{f"{self.model.validity_field_name}__startswith__gt": at_date},
        )

    def not_current(self, asof_transaction=None) -> QuerySet:
        """
        Filter the queryset to only those TrackedModels that are not the latest
        approved versions as of the given Transaction.

        :param transaction Transaction: The transaction to limit versions to.
        :rtype QuerySet:
        """
        current = self.approved_up_to_transaction(asof_transaction)

        return self.difference(current)

    def as_at(self, date: date) -> QuerySet:
        """
        Return the instances of the model that were represented at a particular
        date.

        If done from the TrackedModel this will return all instances of all
        tracked models as represented at a particular date.

        :param date date: Exclude results with validity periods that do not contain this
        date.
        :rtype QuerySet:
        """
        return self.filter(valid_between__contains=date)

    def as_at_today(self) -> QuerySet:
        """
        Return the instances of the model that are represented at the current
        date.

        If done from the TrackedModel this will return all instances of all
        tracked models as represented at the current date.

        :rtype QuerySet:
        """
        return self.as_at(date.today())


class TransactionPartitionQuerySet(QuerySet):
    @classmethod
    def approved_query_filter(cls, prefix=""):
        from common.models.transactions import TransactionPartition

        return Q(
            **{
                f"{prefix}transaction__partition__in": TransactionPartition.approved_partitions(),
            }
        )

    @classmethod
    def as_at_transaction_filter(cls, transaction, prefix=""):
        """
        This Filter returns models that exist as of the provided transaction.

        If `transaction` is in draft this also includes draft versions
        in the same workbasket.

        This differs from `object.versions` which includes all draft versions.

        At the database level, that is any transaction in this partition with lower
        order (and in this workbasket in the case of DRAFT), or any transaction
        in an earlier partition [1].

        [1] Partition values roughly encode temporal data:  Each value represents
        an "era" of transactions, starting at SEED_FILE and ending at DRAFT.
        """
        from common.models.transactions import TransactionPartition

        this_partition = {
            f"{prefix}transaction__partition": transaction.partition,
            f"{prefix}transaction__order__lte": transaction.order,
        }

        workbasket_select = Q(
            **{
                f"{prefix}transaction__partition": TransactionPartition.DRAFT,
                f"{prefix}transaction__workbasket__id": transaction.workbasket_id,
            }
        ) | Q(
            **{
                f"{prefix}transaction__partition__in": TransactionPartition.approved_partitions(),
            }
        )

        earlier_partition = {
            f"{prefix}transaction__partition__lt": transaction.partition,
        }

        return (Q(**this_partition) & workbasket_select) | Q(**earlier_partition)
