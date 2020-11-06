import re
from datetime import datetime

from django.apps import apps
from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models import CharField, Case
from django.db.models import F, Q, Value, When
from django.db.models import QuerySet
from django.db.models.query_utils import DeferredAttribute
from django.template import loader
from django.utils import timezone
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet
from treebeard.mp_tree import MP_NodeQuerySet

from common import exceptions
from common import validators
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
        return self.as_at(timezone.now())

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
        return self.filter(query) | in_workbasket.filter(successor__isnull=True)

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

    def annotate_record_codes(self) -> QuerySet:
        """
        :return: Query annotated with record_code and subrecord_code.
        """
        # Generates case statements to do the mapping from model to record_code and subrecord_code.
        q = self.annotate(
            record_code=Case(
                *(TrackedModelQuerySet._when_model_record_codes()),
                output_field=CharField(),
            ),
            subrecord_code=Case(
                *(TrackedModelQuerySet._when_model_subrecord_codes()),
                output_field=CharField(),
            ),
        )
        return q

    @staticmethod
    def _when_model_record_codes():
        """
        Iterate all TrackedModel subclasses, generating When statements that map
        the model to its record_code.

        If any of the models start using a foreign key then this function will need to be updated.
        """
        return [
            When(
                Q(
                    polymorphic_ctype__app_label=model._meta.app_label,
                    polymorphic_ctype__model=model._meta.model_name,
                ),
                then=Value(model.record_code),
            )
            for model in TrackedModel.get_subclasses()
        ]

    @staticmethod
    def _subrecord_value_or_f(model):
        """
        Return F function or Value to fetch subrecord_code in a query.
        """
        if isinstance(model.subrecord_code, DeferredAttribute):
            return F(f"{model._meta.model_name}__subrecord_code")
        return Value(model.subrecord_code)

    @staticmethod
    def _when_model_subrecord_codes():
        """
        Iterate all TrackedModel subclasses, generating When statements that map
        the model to its subrecord_code.

        This function is a little more complex than when_model_record_codes as subrecord_code
        may be a standard class attribute or a ForeignKey.
        """
        return [
            When(
                Q(
                    polymorphic_ctype__app_label=model._meta.app_label,
                    polymorphic_ctype__model=model._meta.model_name,
                ),
                then=TrackedModelQuerySet._subrecord_value_or_f(model),
            )
            for model in TrackedModel.get_subclasses()
        ]


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
    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.PROTECT,
        related_name="tracked_models",
    )
    predecessor = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="successor",
        related_query_name="successor",
    )

    update_type = models.PositiveSmallIntegerField(
        choices=validators.UpdateType.choices
    )

    objects = PolymorphicManager.from_queryset(TrackedModelQuerySet)()

    identifying_fields = ("sid",)

    taric_template = None

    @staticmethod
    def get_subclasses():
        """
        :return: list of all subclasses of TrackedModel
        """
        # Using the django.apps registry generates 0 queries.
        return [
            model
            for table_name_model in apps.all_models.values()
            for model in table_name_model.values()
            if model is not TrackedModel and issubclass(model, TrackedModel)
        ]

    def get_taric_template(self):
        """
        Generate a TARIC XML template name for the given class.

        Any TrackedModel must be representable via a TARIC compatible XML record.
        To facilitate this
        """

        if self.taric_template:
            return self.taric_template
        class_name = self.__class__.__name__

        # replace namesLikeThis to names_Like_This
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", class_name)
        # replace names_LIKEthis to names_like_this
        name = re.sub(r"([A-Z]{2,})([a-z0-9_])", r"\1_\2", name).lower()

        template_name = f"taric/{name}.xml"
        try:
            loader.get_template(template_name)
        except loader.TemplateDoesNotExist as e:
            raise loader.TemplateDoesNotExist(
                f"""Taric template does not exist for {class_name}. All classes that \
inherit TrackedModel must either:
    1) Have a matching taric template with a snake_case name matching the class at \
"taric/{{snake_case_class_name}}.xml". In this case it should be: "{template_name}".
    2) A taric_template attribute, pointing to the correct template.
    3) Override the get_taric_template method, returning an existing template."""
            ) from e

        return template_name

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
        new_object_kwargs.setdefault("update_type", validators.UpdateType.UPDATE)
        new_object_kwargs["predecessor"] = self
        new_object_kwargs.pop("polymorphic_ctype")
        new_object_kwargs.pop("trackedmodel_ptr")

        new_object_kwargs.update(kwargs)

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

        return new_object

    def get_versions(self):
        query = Q()
        for field in self.identifying_fields:
            query &= Q(**{field: getattr(self, field)})
        return self.__class__.objects.filter(query).order_by("-created_at")

    def get_latest_version(self):
        return self.__class__.objects.get_latest_version(
            **{field: getattr(self, field) for field in self.identifying_fields}
        )

    def validate_workbasket(self):
        pass

    def add_to_workbasket(self, workbasket):
        if workbasket == self.workbasket:
            self.save()
            return self

        return self.new_draft(workbasket=workbasket)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return ", ".join(
            f"{field}={getattr(self, field, None)}" for field in self.identifying_fields
        )


class NumericSID(models.PositiveIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["validators"] = [validators.NumericSIDValidator()]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["validators"]
        return name, path, args, kwargs


class SignedIntSID(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        return name, path, args, kwargs


class ShortDescription(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 500
        kwargs["blank"] = True
        kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["blank"]
        del kwargs["null"]
        return name, path, args, kwargs


class ApplicabilityCode(models.PositiveSmallIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = validators.ApplicabilityCode.choices
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["choices"]
        return name, path, args, kwargs
