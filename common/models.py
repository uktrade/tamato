from datetime import datetime

from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models import QuerySet
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet
from treebeard.mp_tree import MP_Node
from treebeard.mp_tree import MP_NodeQuerySet

from common import exceptions


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
        return self.filter(successor__isnull=True)

    def since_transaction(self, transaction_id: int) -> QuerySet:
        """
        Get all instances of an object since a certain transaction (i.e. since a particular
        workbasket was accepted).

        This will not include objects without a transaction ID - thus excluding rows which
        have not been accepted yet.

        If done from the TrackedModel this will return all objects from all transactions since
        the given transaction.
        """
        return self.filter(workbasket__transaction__id__gt=transaction_id)

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
        return self.as_at(datetime.now())

    def get_version(self, **kwargs):
        for field in self.model.identifying_fields:
            if field not in kwargs:
                raise exceptions.NoIdentifyingValuesGivenError(
                    f"Field {field} expected but not found."
                )
        return self.get(**kwargs)

    def get_latest_version(self, **kwargs):
        """
        Gets the latest version of a specific object.
        """
        return self.get_version(successor__isnull=True, **kwargs)

    def get_current_version(self, **kwargs):
        """
        Gets the current version of a specific object.
        """
        return self.active().get_version(**kwargs)

    def get_first_version(self, **kwargs):
        """
        Get the original version of a specific object.
        """
        return self.get_version(predecessor__isnull=True, **kwargs)


class PolymorphicMPTreeQuerySet(TrackedModelQuerySet, MP_NodeQuerySet):
    """
    Combines QuerySets from the TrackedModel system and the MPTT QuerySet from django-treebeard.

    Treebeards QuerySet only overrides the `.delete` method, whereas the Polymorphic QuerySet
    never changes `.delete` so they should work together well.
    """


class PolymorphicMPTreeManager(PolymorphicManager):
    def get_queryset(self):
        """
        The only change the MP_NodeManager from django-treebeard adds to the manager is
        to order the queryset by the path - effectively putting things in tree order.

        This makes it easier to inherit the PolymorphicManager instead which does more work.

        PolymorphicModel also requires the manager to inherit from PolymorphicManager.
        """
        qs = super().get_queryset()
        return qs.order_by("path")


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    valid_between = DateTimeRangeField()

    class Meta:
        abstract = True


class TrackedModel(PolymorphicModel):
    workbasket = models.ForeignKey("workbaskets.WorkBasket", on_delete=models.PROTECT)
    predecessor = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="successor",
        related_query_name="successor",
    )

    objects = PolymorphicManager.from_queryset(TrackedModelQuerySet)()

    identifying_fields = ("sid",)

    def new_draft(self, workbasket, save=True, **kwargs):
        if hasattr(self, "successor"):
            raise exceptions.AlreadyHasSuccessorError(
                f"Object with PK: {self.pk} already has a successor, can't have multiple successors. "
                f"Use objects.get_latest_version to find the latest instance of this object without a "
                f"successor."
            )
        cls = self.__class__

        new_object_kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name != "id"
        }

        new_object_kwargs["workbasket"] = workbasket
        new_object_kwargs["predecessor"] = self
        new_object_kwargs.pop("polymorphic_ctype")
        new_object_kwargs.pop("trackedmodel_ptr")

        new_object_kwargs.update(kwargs)

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

        return new_object

    def validate_workbasket(self):
        pass
