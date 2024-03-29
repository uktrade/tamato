from typing import Type

from django.db.models.fields import Field
from django.urls import NoReverseMatch
from django.urls import reverse

from common.business_rules import NoBlankDescription
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.exceptions import NoDescriptionError
from common.models.managers import TrackedModelManager
from common.models.mixins.validity import ValidityStartMixin
from common.models.mixins.validity import ValidityStartQueryset
from common.models.tracked_qs import TrackedModelQuerySet
from common.models.tracked_utils import get_relations
from common.util import classproperty
from common.validators import UpdateType
from workbaskets.validators import WorkflowStatus


class DescriptionQueryset(ValidityStartQueryset, TrackedModelQuerySet):
    pass


class DescriptionMixin(ValidityStartMixin):
    objects = TrackedModelManager.from_queryset(DescriptionQueryset)()

    business_rules = (
        NoBlankDescription,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    @classproperty
    def described_object_field(cls) -> Field:
        for rel in get_relations(cls).keys():
            if rel.name.startswith("described_"):
                return rel
        raise TypeError(f"{cls} should have a described field.")

    @classproperty
    def validity_over(cls):
        return cls.described_object_field.name

    def get_described_object(self):
        return getattr(self, self.described_object_field.name)

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = self.get_identifying_fields()
            described_object = self.get_described_object()

            if action == "detail":
                url = described_object.get_url()
                if url:
                    return url + "#descriptions"
                return
            elif (
                action == "edit"
                and self.transaction.workbasket.status == WorkflowStatus.EDITING
            ):
                # Edits in WorkBaskets that are in EDITING state get real
                # changes via DB updates, not newly created UPDATE instances.
                if self.update_type == UpdateType.CREATE:
                    action += "-create"
                elif self.update_type == UpdateType.UPDATE:
                    action += "-update"

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


class DescribedMixin:
    """Mixin adding convenience methods for TrackedModels with associated
    Descriptions."""

    @classproperty
    def description_type(cls) -> Type[DescriptionMixin]:
        return cls._meta.get_field("descriptions").remote_field.model

    @classmethod
    def create(cls, *, description: str, update_type=UpdateType.CREATE, **kwargs):
        described = cls.objects.create(
            update_type=update_type,
            **kwargs,
        )

        cls.description_type.objects.create(
            description=description,
            validity_start=described.valid_between.lower,
            transaction=described.transaction,
            update_type=update_type,
            **{cls.description_type.described_object_field.name: described},
        )

        return described

    def get_descriptions(self) -> TrackedModelQuerySet:
        """
        Get the latest descriptions related to this instance of the Tracked
        Model.

        If there is no Description relation existing a `NoDescriptionError` is raised.

        If a transaction is provided then all latest descriptions that are either approved
        or in the workbasket of the transaction up to the transaction will be provided.
        """
        try:
            descriptions_model = self.descriptions.model
        except AttributeError as e:
            raise NoDescriptionError(
                f"Model {self.__class__.__name__} has no descriptions relation.",
            ) from e

        for field, model in get_relations(descriptions_model).items():
            if isinstance(self, model):
                field_name = field.name
                break
        else:
            raise NoDescriptionError(
                f"No foreign key back to model {self.__class__.__name__} "
                f"found on description model {descriptions_model.__name__}.",
            )

        filter_kwargs = {
            f"{field_name}__{key}": value
            for key, value in self.get_identifying_fields().items()
        }

        query = descriptions_model.objects.filter(**filter_kwargs).order_by(
            *descriptions_model._meta.ordering,
        )

        return query.current()

    def get_description(self):
        return self.get_descriptions().last()

    @property
    def autocomplete_label(self):
        description = self.get_description()
        if not description:
            return f"{self}"

        return f"{self} - {description.description}"
