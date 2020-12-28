from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models import Case
from django.db.models import F
from django.db.models import Field
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models import When
from django.db.models.query_utils import DeferredAttribute
from django.db.transaction import atomic
from django.template import loader
from django.utils import timezone
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet

from common import exceptions
from common import validators
from workbaskets.validators import WorkflowStatus


class IllegalSaveError(Exception):
    pass


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
        in_workbasket = self.filter(transaction__workbasket=workbasket)

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
            transaction__workbasket__status__in=WorkflowStatus.approved_statuses(),
            transaction__workbasket__approver__isnull=False,
        )

    def approved_or_in_workbasket(self, workbasket):
        """
        Get objects which have been approved or are in the specified workbasket.
        """

        return self.filter(
            Q(transaction__workbasket=workbasket)
            | Q(
                transaction__workbasket__status__in=WorkflowStatus.approved_statuses(),
                transaction__workbasket__approver__isnull=False,
            )
        )

    def annotate_record_codes(self) -> QuerySet:
        """
        :return: Query annotated with record_code and subrecord_code.
        """
        # Generates case statements to do the mapping from model to record_code and subrecord_code.
        return self.annotate(
            record_code=Case(
                *(TrackedModelQuerySet._when_model_record_codes()),
                output_field=models.CharField(),
            ),
            subrecord_code=Case(
                *(TrackedModelQuerySet._when_model_subrecord_codes()),
                output_field=models.CharField(),
            ),
        )

    def _get_related_lookups(
        self, model, *lookups, prefix="", recurse_level=0
    ) -> List[str]:
        related_lookups = []
        for relation, _ in model.get_relations():
            if lookups and relation.name not in lookups:
                continue
            related_lookups.append(f"{prefix}{relation.name}")
            related_lookups.append(f"{prefix}{relation.name}__version_group")
            related_lookups.append(
                f"{prefix}{relation.name}__version_group__current_version"
            )

            if recurse_level:
                related_lookups.extend(
                    self._get_related_lookups(
                        model,
                        *lookups,
                        prefix=f"{prefix}{relation.name}__version_group__current_version__",
                        recurse_level=recurse_level - 1,
                    )
                )
        return related_lookups

    def with_latest_links(self, *lookups, recurse_level=0) -> QuerySet:
        related_lookups = self._get_related_lookups(
            self.model, *lookups, recurse_level=recurse_level
        )
        return self.select_related(
            "version_group", "version_group__current_version", *related_lookups
        )

    def get_queryset(self):
        return self.annotate_record_codes().order_by("record_code", "subrecord_code")

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
            for model in TrackedModel.__subclasses__()
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
            for model in TrackedModel.__subclasses__()
        ]


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    valid_between = DateTimeRangeField()

    class Meta:
        abstract = True


class VersionGroup(models.Model):
    current_version = models.ForeignKey(
        "common.TrackedModel",
        on_delete=models.SET_NULL,
        unique=True,
        null=True,
        related_name="+",
        related_query_name="is_current",
    )


class TrackedModel(PolymorphicModel):
    transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=models.PROTECT,
        related_name="tracked_models",
        editable=False,
    )

    update_type = models.PositiveSmallIntegerField(
        choices=validators.UpdateType.choices
    )

    version_group = models.ForeignKey(
        VersionGroup, on_delete=models.PROTECT, related_name="versions"
    )

    objects = PolymorphicManager.from_queryset(TrackedModelQuerySet)()

    business_rules: Iterable = ()
    identifying_fields = ("sid",)
    taric_template = None

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
                f"Taric template does not exist for {class_name}. All classes that "
                "inherit TrackedModel must either:\n"
                "    1) Have a matching taric template with a snake_case name matching "
                'the class at "taric/{snake_case_class_name}.xml". In this case it '
                f'should be: "{template_name}".\n'
                "    2) A taric_template attribute, pointing to the correct template.\n"
                "    3) Override the get_taric_template method, returning an existing "
                "template."
            ) from e

        return template_name

    def new_draft(self, workbasket, save=True, **kwargs):
        cls = self.__class__

        new_object_kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name
            not in (self._meta.pk.name, "polymorphic_ctype", "trackedmodel_ptr", "id")
        }

        new_object_kwargs["transaction"] = workbasket.new_transaction()
        new_object_kwargs["update_type"] = validators.UpdateType.UPDATE

        new_object_kwargs.update(kwargs)

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

        return new_object

    def get_versions(self):
        if hasattr(self, "version_group"):
            return self.version_group.versions.all()

        query = Q(**self.get_identifying_fields())
        return self.__class__.objects.filter(query).order_by("-pk")

    def get_latest_version(self):
        current_version = self.version_group.current_version
        if current_version is None:
            raise self.__class__.DoesNotExist("Object has no current version")
        return current_version

    def identifying_fields_unique(
        self, identifying_fields: Optional[Iterable[str]] = None
    ) -> bool:
        if identifying_fields is None:
            identifying_fields = self.identifying_fields

        # TODO this needs to handle deleted trackedmodels
        return (
            self.__class__.objects.filter(
                **{field: getattr(self, field) for field in identifying_fields}
            ).count()
            <= 1
        )

    def identifying_fields_to_string(
        self, identifying_fields: Optional[Iterable[str]] = None
    ) -> str:
        field_list = []
        for field, value in self.get_identifying_fields(identifying_fields).items():
            field_list.append(f"{field}={str(value)}")

        return ", ".join(field_list)

    def _get_version_group(self) -> VersionGroup:
        if self.update_type == validators.UpdateType.CREATE:
            return VersionGroup.objects.create()
        return self.get_versions().first().version_group

    def _can_write(self):
        return not (
            self.pk
            and self.transaction.workbasket.status in WorkflowStatus.approved_statuses()
        )

    def get_identifying_fields(
        self, identifying_fields: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        identifying_fields = identifying_fields or self.identifying_fields
        fields = {}

        for field in identifying_fields:
            value = self
            for layer in field.split("__"):
                value = getattr(value, layer)
                if value is None:
                    break
            fields[field] = value

        return fields

    @atomic
    def save(self, *args, force_write=False, **kwargs):
        if not force_write and not self._can_write():
            raise IllegalSaveError(
                "TrackedModels cannot be updated once written and approved. "
                "If writing a new row, use `.new_draft` instead"
            )

        if not hasattr(self, "version_group"):
            self.version_group = self._get_version_group()

        return_value = super().save(*args, **kwargs)

        if self.transaction.workbasket.status in WorkflowStatus.approved_statuses():
            self.version_group.current_version = self
            self.version_group.save()

        return return_value

    @property
    def current_version(self) -> TrackedModel:
        current_version = self.version_group.current_version
        if current_version is None:
            raise self.__class__.DoesNotExist("Object has no current version")
        return current_version

    @classmethod
    def get_relations(cls) -> List[Tuple[Field, Type[TrackedModel]]]:
        """
        Find all foreign key and one-to-one relations on an object and return a list containing
        tuples of the field instance and the related model it links to.
        """
        return [
            (f, f.related_model)
            for f in cls._meta.get_fields()
            if (f.many_to_one or f.one_to_one)
            and not f.auto_created
            and f.concrete
            and f.model == cls
            and issubclass(f.related_model, TrackedModel)
        ]

    def __getattr__(self, item: str):
        """
        Add the ability to get the current instance of a related object through an attribute.
        For example if a model is like so:

        .. code:: python
            class ExampleModel(TrackedModel):
                # must be a TrackedModel
                other_model = models.ForeignKey(OtherModel, on_delete=models.PROTECT)

        The latest version of the relation can be accessed via:

        .. code:: python
            example_model = ExampleModel.objects.first()
            example_model.other_model_current  # Gets the latest version
        """
        relations = {
            f"{relation.name}_current": relation.name
            for relation, model in self.get_relations()
        }
        if item not in relations:
            try:
                return super().__getattr__(item)
            except AttributeError as e:
                raise AttributeError(
                    f"{item} does not exist on {self.__class__.__name__}"
                ) from e
        return getattr(self, relations[item]).current_version

    def __str__(self):
        return ", ".join(
            f"{field}={getattr(self, field, None)}" for field in self.identifying_fields
        )
