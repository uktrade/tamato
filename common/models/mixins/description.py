from __future__ import annotations

from typing import Any
from typing import Iterable
from typing import Optional
from typing import Protocol
from typing import Union

from django.db import models
from django.db.models.fields import Field
from django.db.models.fields.related import RelatedField
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager

from common.business_rules import NoBlankDescription
from common.business_rules import UpdateValidity
from common.exceptions import NoDescriptionError
from common.fields import LongDescription
from common.fields import ShortDescription
from common.models.mixins.validity import ValidityStartMixin
from common.models.mixins.validity import ValidityStartQueryset
from common.models.records import TrackedModelQuerySet


class DescriptionQueryset(ValidityStartQueryset, TrackedModelQuerySet):
    pass


class DescriptionProtocol(Protocol):
    @property
    def description(self) -> Union[LongDescription, ShortDescription]:
        ...

    @property
    def described_object(self) -> Optional[models.Model]:
        ...

    @classmethod
    @property
    def relations(cls) -> dict[RelatedField, models.Model]:
        ...

    @classmethod
    @property
    def described_object_field(cls) -> Field:
        ...


class DescriptionMixin(ValidityStartMixin):
    objects = PolymorphicManager.from_queryset(DescriptionQueryset)()

    business_rules = (
        NoBlankDescription,
        UpdateValidity,
    )

    @classmethod
    @property
    def described_object_field(cls: type[DescriptionProtocol]) -> Field:
        try:
            return next(
                field
                for field in cls._meta.local_fields
                if field.many_to_one
                and field.model is cls
                and field.name.startswith("described_")
            )
        except StopIteration:
            raise TypeError(f"{cls} should have a described field.")

    @property
    def described_object(self) -> Optional[models.Model]:
        for field in self._meta.local_fields:
            if field.many_to_one and field.model == self.__class__:
                return getattr(self, field.name)

    @classmethod
    @property
    def validity_over(cls):
        return cls.described_object_field.name

    def get_described_object(self):
        return getattr(self, self.described_object_field.name)

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = self.get_identifying_field_values()
            described_object = self.get_described_object()
            for field, value in described_object.get_identifying_fields().items():
                kwargs[f"{self.described_object_field.name}__{field}"] = value
        try:
            return reverse(
                f"{self.get_url_pattern_name_prefix()}-ui-{action}",
                kwargs=kwargs,
            )
        except NoReverseMatch:
            return

    def __str__(self):
        return self.identifying_fields_to_string(
            identifying_fields=(
                self.described_object_field.name,
                "validity_start",
            ),
        )

    class Meta:
        abstract = True


class TrackedModelWithDescriptions(Protocol):
    @property
    def descriptions(self) -> TrackedModelQuerySet:
        ...

    @property
    def transaction(self):
        ...

    def get_identifying_field_values(
        self,
        identifying_fields: Optional[Iterable[str]] = None,
    ) -> dict[str, Any]:
        ...

    def get_descriptions(self, transaction=None) -> TrackedModelQuerySet:
        ...

    def get_description(self) -> DescriptionProtocol:
        ...


class DescribedMixin:
    """Mixin adding convenience methods for TrackedModels with associated
    Descriptions."""

    def get_descriptions(
        self: TrackedModelWithDescriptions,
        transaction=None,
    ) -> TrackedModelQuerySet:
        """
        Get the latest descriptions related to this instance of the Tracked
        Model.

        If there is no Description relation existing a `NoDescriptionError` is raised.

        If a transaction is provided then all latest descriptions that are either approved
        or in the workbasket of the transaction up to the transaction will be provided.
        """
        Description = self.descriptions.model

        try:
            described_obj = next(
                field.name
                for field, model in Description.relations.items()
                if isinstance(self, model)
            )

        except StopIteration:
            raise NoDescriptionError(
                f"No foreign key back to model {self.__class__.__name__} "
                f"found on description model {Description.__name__}.",
            )

        return Description.objects.latest_approved(transaction=transaction).filter(
            **{
                f"{described_obj}__{key}": value
                for key, value in self.get_identifying_field_values().items()
            }
        )

    def get_description(self: TrackedModelWithDescriptions) -> DescriptionProtocol:
        return self.get_descriptions(transaction=self.transaction).last()

    @property
    def structure_description(self) -> str:
        return self.get_description().description
