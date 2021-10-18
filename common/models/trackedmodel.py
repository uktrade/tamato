from __future__ import annotations

from copy import copy
from typing import Any
from typing import Iterable
from typing import Optional
from typing import TypeVar
from typing import Union

from django.db import models
from django.db.models import Expression
from django.db.models import F
from django.db.models import Field
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.options import Options
from django.db.transaction import atomic
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from common.exceptions import IllegalSaveError
from common.fields import NumericSID
from common.fields import SignedIntSID
from common.models.trackedmodel_queryset import TrackedModelQuerySet
from common.models.versiongroup import VersionGroup
from common.util import classproperty
from common.util import get_field_tuple
from common.validators import UpdateType
from workbaskets.validators import WorkflowStatus

T = TypeVar("T", bound="TrackedModel")


class TrackedModel(PolymorphicModel):
    transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=models.PROTECT,
        related_name="tracked_models",
        editable=False,
    )

    update_type = models.PositiveSmallIntegerField(
        choices=UpdateType.choices,
        db_index=True,
    )
    """
    The change that was made to the model when this version of the model was
    authored.

    The first version should always have :data:`~validators.UpdateType.CREATE`,
    subsequent versions will have :data:`~validators.UpdateType.UPDATE` and the
    final version will have :data:`~validators.UpdateType.DELETE`. Deleted
    models that reappear for the same :attr:`identifying_fields` will have a new
    :attr:`version_group` created.
    """

    version_group = models.ForeignKey(
        VersionGroup,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    """
    Each version group contains all of the versions of the same logical model.

    When a new version of a model is authored (e.g. to
    :data:`~validators.UpdateType.DELETE` it) a new model row is created and
    added to the same version group as the existing model being changed.

    Models are identified logically by their :attr:`identifying_fields`, so
    within one version group all of the models should have the same values for
    these fields.
    """

    objects = PolymorphicManager.from_queryset(
        TrackedModelQuerySet,
    )()

    business_rules: Iterable = ()
    indirect_business_rules: Iterable = ()

    record_code: int
    """
    The type id of this model's type family in the TARIC specification.

    This number groups together a number of different models into 'records'.
    Where two models share a record code, they are conceptually expressing
    different properties of the same logical model.

    In theory each :class:`~common.transactions.Transaction` should only contain
    models with a single :attr:`record_code` (but differing
    :attr:`subrecord_code`.)
    """

    subrecord_code: int
    """
    The type id of this model in the TARIC specification. The
    :attr:`subrecord_code` when combined with the :attr:`record_code` uniquely
    identifies the type within the specification.

    The subrecord code gives the intended order for models in a transaction,
    with comparatively smaller subrecord codes needing to come before larger
    ones.
    """

    identifying_fields: Iterable[str] = ("sid",)
    """
    The fields which together form a composite unique key for each model.

    The system ID (or SID) field is normally the unique identifier of a TARIC
    model, but in places where this does not exist models can declare their own.
    (Note that because multiple versions of each model will exist this does not
    actually equate to a ``UNIQUE`` constraint in the database.)
    """

    def __copy__(self: T) -> T:
        """Return a shallow copy of a TrackedModel."""

        class_ = self.__class__

        kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.get_fields()
            if (
                field.concrete
                and not field.auto_created
                and field.name != "transaction",
            )
        }

        return class_(**kwargs)

    def build_new_version(
        self: T,
        update_type: UpdateType = UpdateType.UPDATE,
        **overrides,
    ) -> T:
        """
        Return a new version of the object. Callers can override existing data
        by passing in keyword args.

        update_type must be UPDATE or DELETE, with UPDATE as the default.
        """

        if update_type not in (
            UpdateType.UPDATE,
            UpdateType.DELETE,
        ):
            raise ValueError("update_type must be UPDATE or DELETE")

        new_object = copy(self)
        new_object.update_type = update_type

        for attr, value in overrides.items():
            setattr(new_object, attr, value)

        return new_object

    # XXX this can probably go
    def get_identifying_field_values(
        self,
        identifying_fields: Optional[Iterable[str]] = None,
    ) -> dict[str, Any]:
        """Get a dictionary of the identifying fields and their values for this
        object."""

        return dict(
            get_field_tuple(self, field_name)
            for field_name in identifying_fields or self.identifying_fields
        )

    def get_versions(self) -> TrackedModelQuerySet:
        """Get all versions of the model."""

        return self.__class__.objects.filter(**self.get_identifying_field_values())

    @property
    def structure_code(self):
        return str(self)

    @property
    def structure_description(self):
        return getattr(self, "description", None)

    @property
    def current_version(self) -> TrackedModel:
        current_version = self.version_group.current_version
        if current_version is None:
            raise self.__class__.DoesNotExist("Object has no current version")
        return current_version

    def version_at(self, transaction) -> TrackedModel:
        return self.get_versions().approved_up_to_transaction(transaction).get()

    # XXX used in
    # common/business_rules.py:104 - get_linked_models
    # common/models/trackedmodel.py:227 - models_linked_to
    # importer/utils.py:134 - build_dependency_tree
    @classproperty
    def relations(cls) -> dict[Field[Any, Any] | ForeignObjectRel, type[TrackedModel]]:
        """
        Returns all the models that are related to this one.

        The link can either be stored on this model (so a one-to-one or a many-
        to-one relationship) or on the related model (so a one-to-many (reverse)
        relationship).
        """
        return {
            f: f.related_model
            for f in cls._meta.get_fields()
            if (f.many_to_one or f.one_to_one or f.one_to_many)
            and f.model == cls
            and f.related_model
            and issubclass(f.related_model, TrackedModel)
            and f.related_model is not TrackedModel
        }

    # XXX used in
    # exporter/views.py:82 - tracked_model_to_activity_stream_item
    # common/models/trackedmodel_queryset.py:211 - _get_current_related_lookups
    @classproperty
    def models_linked_to(
        cls,
    ) -> dict[Union[Field, ForeignObjectRel], type[TrackedModel]]:
        """Returns all the models that are related to this one via a foreign key
        stored on this model (one-to-many reverse related models are not
        included in the returned results)."""
        return {
            f: r
            for f, r in cls.relations.items()
            if (f.many_to_one or f.one_to_one) and not f.auto_created and f.concrete
        }

    _meta: Options

    @classproperty
    def auto_value_fields(cls) -> set[Field]:
        """Returns the set of fields on this model that should have their value
        set automatically on save, excluding any primary keys."""
        return {
            f
            for f in cls._meta.get_fields()
            if isinstance(f, (SignedIntSID, NumericSID))
        }

    # Fields that we don't want to copy from one object to a new one, either
    # because they will be set by the system automatically or because we will
    # always want to override them.
    # XXX used in
    # common/models/trackedmodel.py:272 - copyable_fields
    # commodities/tests/conftest.py:62 - copy_commodity
    system_set_field_names = {
        "is_current",
        "version_group",
        "polymorphic_ctype",
        "id",
        "update_type",
        "trackedmodel_ptr",
        "transaction",
    }

    # XXX used in
    # common/models/trackedmodel.py:315 - copy
    # common/tests/util.py:126 - get_checkable_data
    @classproperty
    def copyable_fields(cls):
        """
        Return the set of fields that can have their values copied from one
        model to another.

        This is anything that is:
        - a native value
        - a foreign key to some other model
        """
        return {
            field
            for field in cls._meta.get_fields()
            if not any((field.many_to_many, field.one_to_many))
            and field.name not in cls.system_set_field_names
        }

    # XXX used in
    # common/models/trackedmodel.py:369 - copy
    @classproperty
    def subrecord_relations(cls):
        """
        Returns a set of relations to this model's TARIC subrecords.

        E.g, a :class:`~measures.models.Measure` and a
        :class:`measures.models.MeasureComponent` are in the same "logical
        record" but are different data models because they are many-to-one.
        """
        return {
            field
            for field in cls._meta.get_fields()
            if field.one_to_many
            and field.related_model is not cls
            and issubclass(field.related_model, TrackedModel)
            and field.related_model.record_code == cls.record_code
        }

    # XXX used in
    # common/models/trackedmodel.py:377 - copy (recursive)
    # common/tests/test_models.py:444 - test_copy
    # common/tests/test_models.py:459 - test_copy_increments_sid_fields
    # common/tests/test_models.py:466 - test_copy_also_copies_dependents
    # measures/tests/test_models.py:205 - test_copy_measure_doesnt_add_export_refund_sids
    # XXX not used anywhere except tests???
    def copy(
        self,
        transaction,
        **overrides: Any,
    ) -> TrackedModel:
        """
        Create a copy of the model as a new logical domain object – i.e. with a
        new version group, new SID (if present) and update type of CREATE.

        Any dependent models that are TARIC subrecords of this model will be
        copied as well. Any many-to-many relationships will also be duplicated
        if they do not have an explicit through model.

        Any overrides passed in as keyword arguments will be applied to the new
        model. If the model uses SIDs, they will be automatically set to the
        next highest available SID. Models with other identifying fields should
        have thier new IDs passed in through overrides.
        """

        # Remove any fields from the basic data that are overriden, because
        # otherwise when we convert foreign keys to IDs (below) Django will
        # ignore the object from the overrides and just take the ID from the
        # basic data.
        basic_fields = self.copyable_fields
        for field_name in overrides:
            field = self._meta.get_field(field_name)
            basic_fields.remove(field)

        # Remove any SIDs from the copied data. This allows them to either
        # automatically pick the next highest value or to be passed in.
        for field in self.auto_value_fields:
            basic_fields.remove(field)

        # Build the dictionary of data that the new model will have. Convert any
        # foreign keys into ids because ``value_from_object`` returns PKs.
        model_data = {
            f.name
            + (
                "_id" if any((f.many_to_one, f.one_to_one)) else ""
            ): f.value_from_object(self)
            for f in basic_fields
        }

        new_object_data = {
            **model_data,
            "transaction": transaction,
            "update_type": UpdateType.CREATE,
            **overrides,
        }

        new_object = type(self).objects.create(**new_object_data)

        # Now copy any many-to-many fields with an auto-created through model.
        # These must be handled after creation of the new model. We only need to
        # do this for auto-created models because others will be handled below.
        deferred_set_fields = {
            field
            for field in self._meta.get_fields()
            if field.many_to_many
            and hasattr(field.remote_field, "through")
            and field.remote_field.through._meta.auto_created
        }
        for field in deferred_set_fields:
            getattr(new_object, field.name).set(field.value_from_object(self))

        # Now go and create copies of all of the models that reference this one
        # with a foreign key that are part of the same record family. Find all
        # of the related models and then recursively call copy on them, but with
        # the new model substituted in place of this one. It's done this way to
        # give these related models a chance to increment SIDs, etc.
        for field in self.subrecord_relations:
            queryset = getattr(self, field.get_accessor_name())
            reverse_field_name = field.field.name
            for model in queryset.approved_up_to_transaction(transaction):
                model.copy(transaction, **{reverse_field_name: new_object})

        return new_object

    @atomic
    def save(self, *args, force_write: bool = False, **kwargs) -> None:
        approved = (
            self.transaction.workbasket.status in WorkflowStatus.approved_statuses()
        )
        read_only = self.pk and approved

        if read_only and not force_write:
            raise IllegalSaveError(
                "TrackedModels cannot be updated once written and approved.",
            )

        self.version_group = self._get_version_group()

        super().save(*args, **kwargs)

        if approved:
            self.version_group.current_version = self
            self.version_group.save(update_fields=["current_version"])

        self._delete_auto_fields()

    def _get_version_group(self) -> VersionGroup:
        """Set the version group if it is not already set, creating a new one if
        no existing version group matches this model's identifying field
        values."""

        try:
            return self.version_group
        except RelatedObjectDoesNotExist:

            # get the version group from the latest approved version of this object
            latest_version = self.get_versions().latest_approved().last()

            if latest_version:
                return latest_version.version_group

            # if there is no existing version group, create one
            if self.update_type == UpdateType.CREATE:
                return VersionGroup.objects.create()

            # XXX what if we are updating an existing model and change its identifying
            # fields such that no version group can be found?

    def _delete_auto_fields(self) -> None:
        """
        If the model contains any fields that are built in the database, the
        fields will still contain the expression objects.

        If we remove them Django will lazy fetch the real values if they are
        accessed.
        """

        auto_fields = {
            field
            for field in self.auto_value_fields
            if field.attname in self.__dict__
            and isinstance(self.__dict__.get(field.attname), (Expression, F))
        }

        for field in auto_fields:
            delattr(self, field.name)

    def __str__(self):
        return ", ".join(
            f"{field}={value}"
            for field, value in self.get_identifying_field_values().items()
        )

    # XXX collisions guaranteed?
    def __hash__(self):
        return hash(f"{__name__}.{self.__class__.__name__}")

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = self.get_identifying_field_values()
        try:
            return reverse(
                f"{self.get_url_pattern_name_prefix()}-ui-{action}",
                kwargs=kwargs,
            )
        except NoReverseMatch:
            return

    def get_url_pattern_name_prefix(self):
        prefix = getattr(self, "url_pattern_name_prefix", None)
        if not prefix:
            prefix = self._meta.verbose_name.replace(" ", "_")
        return prefix
