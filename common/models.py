from __future__ import annotations

import re
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Type

from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db import transaction
from django.db.models import Field
from django.db.models import Q
from django.template import loader
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from common import validators
from common.querysets import TrackedModelQuerySet
from workbaskets.validators import WorkflowStatus


class IllegalSaveError(Exception):
    pass


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
    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.PROTECT,
        related_name="tracked_models",
    )

    update_type = models.PositiveSmallIntegerField(
        choices=validators.UpdateType.choices
    )

    version_group = models.ForeignKey(
        VersionGroup, on_delete=models.PROTECT, related_name="versions"
    )

    objects = PolymorphicManager.from_queryset(TrackedModelQuerySet)()

    identifying_fields = ("sid",)

    taric_template = None

    def get_taric_template(self) -> str:
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

    def new_draft(self, workbasket, save: bool = True, **kwargs) -> TrackedModel:
        cls = self.__class__

        new_object_kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name
            not in (self._meta.pk.name, "polymorphic_ctype", "trackedmodel_ptr", "id")
        }

        new_object_kwargs["workbasket"] = workbasket
        new_object_kwargs["update_type"] = validators.UpdateType.UPDATE

        new_object_kwargs.update(kwargs)

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

        return new_object

    def get_versions(self) -> TrackedModelQuerySet:
        if hasattr(self, "version_group"):
            return self.version_group.versions.all()

        query = Q(**self.get_identifying_fields())
        return self.__class__.objects.filter(query).order_by("-pk")

    def validate_workbasket(self):
        pass

    def add_to_workbasket(self, workbasket) -> TrackedModel:
        if workbasket == self.workbasket:
            self.save()
            return self

        return self.new_draft(workbasket=workbasket)

    def _get_version_group(self) -> VersionGroup:
        if self.update_type == validators.UpdateType.CREATE:
            return VersionGroup.objects.create()
        return self.get_versions().first().version_group

    def _can_write(self) -> bool:
        return not (
            self.pk and self.workbasket.status in WorkflowStatus.approved_statuses()
        )

    def get_identifying_fields(self) -> Dict[str, Any]:
        fields = {}

        for field in self.identifying_fields:
            value = self
            for layer in field.split("__"):
                value = getattr(value, layer)
            fields[field] = value

        return fields

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

    @transaction.atomic
    def save(self, *args, force_write=False, **kwargs):
        if not force_write and not self._can_write():
            raise IllegalSaveError(
                "TrackedModels cannot be updated once written and approved. "
                "If writing a new row, use `.new_draft` instead"
            )

        if not hasattr(self, "version_group"):
            self.version_group = self._get_version_group()

        self.full_clean()
        return_value = super().save(*args, **kwargs)

        if self.workbasket.status in WorkflowStatus.approved_statuses():
            self.version_group.current_version = self
            self.version_group.save()

        return return_value

    def __str__(self):
        return ", ".join(
            f"{field}={getattr(self, field, None)}" for field in self.identifying_fields
        )
