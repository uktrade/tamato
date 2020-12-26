from datetime import datetime

from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone
from polymorphic.query import PolymorphicQuerySet

from common import exceptions
from workbaskets.validators import WorkflowStatus


class TrackedModelQuerySet(PolymorphicQuerySet):
    def current(self) -> QuerySet:
        """
        Get all the current versions of the model being queried.

        Current is defined as the last row relating to the history of an object.
        this may include current operationally live rows, it will often also mean
        rows that are not operationally live yet but may be soon. It could also include
        rows which were operationally live, are no longer operationally live, but have
        no new row to supercede them.

        If done from the TrackedModel this will return the current objects for all tracked
        models.
        """
        return self.filter(is_current__isnull=False)

    def since_transaction(self, transaction_id: int) -> QuerySet:
        """
        Get all instances of an object since a certain transaction (i.e. since a particular
        workbasket was accepted).

        This will not include objects without a transaction ID - thus excluding rows which
        have not been accepted yet.

        If done from the TrackedModel this will return all objects from all transactions since
        the given transaction.
        """
        return self.filter(transaction__id__gt=transaction_id)

    def as_at(self, date: datetime) -> QuerySet:
        """
        Return the instances of the model that were represented at a particular date.

        If done from the TrackedModel this will return all instances of all tracked models
        as represented at a particular date.
        """
        return self.filter(valid_between__contains=date)

    def active(self) -> QuerySet:
        """
        Return the instances of the model that are represented at the current date.

        If done from the TrackedModel this will return all instances of all tracked models
        as represented at the current date.
        """
        return self.as_at(timezone.now())

    def get_versions(self, **kwargs) -> QuerySet:
        for field in self.model.identifying_fields:
            if field not in kwargs:
                raise exceptions.NoIdentifyingValuesGivenError(
                    f"Field {field} expected but not found."
                )
        return self.filter(**kwargs)

    def get_latest_version(self, **kwargs):
        """
        Gets the latest version of a specific object.
        """
        return self.get_versions(**kwargs).current().get()

    def get_current_version(self, **kwargs):
        """
        Gets the current version of a specific object.
        """
        return self.get_versions(**kwargs).active().get()

    def get_first_version(self, **kwargs):
        """
        Get the original version of a specific object.
        """
        return self.get_versions(**kwargs).order_by("id").first()

    def excluding_versions_of(self, version_group):
        return self.exclude(version_group=version_group)

    def with_workbasket(self, workbasket):
        """
        Add the latest versions of objects from the specified workbasket.
        """

        if workbasket is None:
            return self

        query = Q()

        # get models in the workbasket
        in_workbasket = self.filter(workbasket=workbasket)

        # remove matching models from the queryset
        for instance in in_workbasket:
            query &= ~Q(
                **{
                    field: getattr(instance, field)
                    for field in self.model.identifying_fields
                }
            )

        # add latest version of models from the current workbasket
        return self.filter(query) | in_workbasket.current()

    def approved(self):
        """
        Get objects which have been approved/sent-to-cds/published
        """
        return self.filter(
            workbasket__status__in=WorkflowStatus.approved_statuses(),
            workbasket__approver__isnull=False,
        )

    def approved_or_in_workbasket(self, workbasket):
        """
        Get objects which have been approved or are in the specified workbasket.
        """

        return self.filter(
            Q(workbasket=workbasket)
            | Q(
                workbasket__status__in=WorkflowStatus.approved_statuses(),
                workbasket__approver__isnull=False,
            )
        )
