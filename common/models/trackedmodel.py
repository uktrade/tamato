from __future__ import annotations

from typing import Any
from typing import Iterable
from typing import Sequence
from typing import Set
from typing import TypeVar

from django.db import models
from django.db.models import F
from django.db.models import Field
from django.db.models import Q
from django.db.models.expressions import Expression
from django.db.models.options import Options
from django.db.models.query import QuerySet
from django.db.transaction import atomic
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel

from common import validators
from common.exceptions import IllegalSaveError
from common.fields import NumericSID
from common.fields import SignedIntSID
from common.models import TimestampedMixin
from common.models.tracked_qs import TrackedModelQuerySet
from common.models.tracked_utils import get_copyable_fields
from common.models.tracked_utils import get_deferred_set_fields
from common.models.tracked_utils import get_models_linked_to
from common.models.tracked_utils import get_relations
from common.models.tracked_utils import get_subrecord_relations
from common.util import classproperty
from common.util import get_accessor
from common.util import get_identifying_fields
from common.util import get_identifying_fields_to_string
from common.validators import UpdateType
from workbaskets.validators import WorkflowStatus


class VersionGroup(TimestampedMixin):
    current_version = models.OneToOneField(
        "common.TrackedModel",
        on_delete=models.SET_NULL,
        null=True,
        related_query_name="is_current",
    )


Cls = TypeVar("Cls", bound="TrackedModel")


class TrackedModel(PolymorphicModel):
    transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=models.PROTECT,
        related_name="tracked_models",
        editable=False,
    )

    update_type: validators.UpdateType = models.PositiveSmallIntegerField(
        choices=validators.UpdateType.choices,
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

    objects: TrackedModelQuerySet = PolymorphicManager.from_queryset(
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

    identifying_fields: Sequence[str] = ("sid",)
    """
    The fields which together form a composite unique key for each model.

    The system ID (or SID) field is normally the unique identifier of a TARIC
    model, but in places where this does not exist models can declare their own.
    (Note that because multiple versions of each model will exist this does not
    actually equate to a ``UNIQUE`` constraint in the database.)
    """

    def new_version(
        self: Cls,
        workbasket,
        transaction=None,
        save: bool = True,
        update_type: UpdateType = UpdateType.UPDATE,
        **overrides,
    ) -> Cls:
        """
        Return a new version of the object. Callers can override existing data
        by passing in keyword args.

        The new version is added to a transaction which is created and added to the passed in workbasket
        (or may be supplied as a keyword arg).

        update_type must be UPDATE or DELETE, with UPDATE as the default.

        By default the new object is saved; this can be disabled by passing save=False.
        """
        if update_type not in (
            validators.UpdateType.UPDATE,
            validators.UpdateType.DELETE,
        ):
            raise ValueError("update_type must be UPDATE or DELETE")

        cls = self.__class__

        new_object_kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field is self._meta.get_field("version_group")
            or field.name not in self.system_set_field_names
        }

        new_object_overrides = {
            name: value
            for name, value in overrides.items()
            if name not in [f.name for f in get_deferred_set_fields(self)]
        }

        new_object_kwargs["update_type"] = update_type
        new_object_kwargs.update(new_object_overrides)

        if transaction is None:
            transaction = workbasket.new_transaction()
        new_object_kwargs["transaction"] = transaction

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

            # TODO: make this work with save=False!
            # Maybe the deferred values could be saved on the model
            # and then handled with a post_save signal?
            deferred_kwargs = {
                field.name: field.value_from_object(self)
                for field in get_deferred_set_fields(self)
            }
            deferred_overrides = {
                name: value
                for name, value in overrides.items()
                if name in [f.name for f in get_deferred_set_fields(self)]
            }
            deferred_kwargs.update(deferred_overrides)
            for field in deferred_kwargs:
                getattr(new_object, field).set(deferred_kwargs[field])

        return new_object

    def get_versions(self):
        if hasattr(self, "version_group"):
            return self.version_group.versions.all()
        query = Q(**get_identifying_fields(self))
        return self.__class__.objects.filter(query)

    def _get_version_group(self) -> VersionGroup:
        if self.update_type == validators.UpdateType.CREATE:
            return VersionGroup.objects.create()
        return self.get_versions().latest_approved().last().version_group

    def _can_write(self):
        return not (
            self.pk
            and self.transaction.workbasket.status in WorkflowStatus.approved_statuses()
        )

    @property
    def structure_code(self):
        return str(self)

    @property
    def current_version(self: Cls) -> Cls:
        current_version = self.version_group.current_version
        if current_version is None:
            raise self.__class__.DoesNotExist("Object has no current version")
        return current_version

    def version_at(self: Cls, transaction) -> Cls:
        return self.get_versions().approved_up_to_transaction(transaction).get()

    _meta: Options

    @classproperty
    def auto_value_fields(cls) -> Set[Field]:
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
    system_set_field_names = {
        "is_current",
        "version_group",
        "polymorphic_ctype",
        "id",
        "update_type",
        "trackedmodel_ptr",
        "transaction",
    }

    def copy(
        self: Cls,
        transaction,
        **overrides: Any,
    ) -> Cls:
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
        basic_fields = get_copyable_fields(self)
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
            "update_type": validators.UpdateType.CREATE,
            **overrides,
        }

        new_object = type(self).objects.create(**new_object_data)

        # Now copy any many-to-many fields with an auto-created through model.
        # These must be handled after creation of the new model. We only need to
        # do this for auto-created models because others will be handled below.
        for field in get_deferred_set_fields(self):
            getattr(new_object, field.name).set(field.value_from_object(self))

        # Now go and create copies of all of the models that reference this one
        # with a foreign key that are part of the same record family. Find all
        # of the related models and then recursively call copy on them, but with
        # the new model substituted in place of this one. It's done this way to
        # give these related models a chance to increment SIDs, etc.
        for field in get_subrecord_relations(self.__class__):
            queryset = getattr(self, field.get_accessor_name())
            reverse_field_name = field.field.name
            for model in queryset.approved_up_to_transaction(transaction):
                model.copy(transaction, **{reverse_field_name: new_object})

        return new_object

    def in_use_by(self, via_relation: str, transaction=None) -> QuerySet[TrackedModel]:
        """
        Returns all of the models that are referencing this one via the
        specified relation and exist as of the passed transaction.

        ``via_relation`` should be the name of a relation, and a ``KeyError``
        will be raised if the relation name is not valid for this model.
        Relations are accessible via get_relations helper method.
        """
        relation = {r.name: r for r in get_relations(self.__class__).keys()}[
            via_relation
        ]
        remote_model = relation.remote_field.model
        remote_field_name = get_accessor(relation.remote_field)

        return remote_model.objects.filter(
            **{f"{remote_field_name}__version_group": self.version_group}
        ).approved_up_to_transaction(transaction)

    def in_use(self, transaction=None, *relations: str) -> bool:
        """
        Returns True if there are any models that are using this one as of the
        specified transaction.

        This can be any model this model is related to, but ignoring any
        subrecords (because e.g. a footnote is not considered "in use by" its
        own description) and then filtering for only things that link _to_ this
        model.

        The list of relations can be filtered by passing in the name of a
        relation. If a name is passed in that does not refer to a relation on
        this model, ``ValueError`` will be raised.
        """
        # Get the list of models that use models of this type.
        class_ = self.__class__
        using_models = set(
            relation.name
            for relation in (
                get_relations(class_).keys()
                - get_subrecord_relations(class_)
                - get_models_linked_to(class_).keys()
            )
        )

        # If the user has specified names, check that they are sane
        # and then filter the relations to them,
        if relations:
            bad_names = set(relations) - set(using_models)
            if any(bad_names):
                raise ValueError(
                    f"{bad_names} are unknown relations; use one of {using_models}",
                )

            using_models = {
                relation for relation in using_models if relation in relations
            }

        # If this model doesn't have any using relations, it cannot be in use.
        if not any(using_models):
            return False

        # If we find any objects for any relation, then the model is in use.
        for relation_name in using_models:
            relation_queryset = self.in_use_by(relation_name, transaction)
            if relation_queryset.exists():
                return True

        return False

    @atomic
    def save(self, *args, force_write=False, **kwargs):
        if not force_write and not self._can_write():
            raise IllegalSaveError(
                "TrackedModels cannot be updated once written and approved. "
                "If writing a new row, use `.new_draft` instead",
            )

        if not hasattr(self, "version_group"):
            self.version_group = self._get_version_group()

        return_value = super().save(*args, **kwargs)

        if self.transaction.workbasket.status in WorkflowStatus.approved_statuses():
            self.version_group.current_version = self
            self.version_group.save()

        auto_fields = {
            field
            for field in self.auto_value_fields
            if field.attname in self.__dict__
            and isinstance(self.__dict__.get(field.attname), (Expression, F))
        }

        # If the model contains any fields that are built in the database, the
        # fields will still contain the expression objects. So remove them now
        # and Django will lazy fetch the real values if they are accessed.
        for field in auto_fields:
            delattr(self, field.name)

        return return_value

    def __str__(self):
        return get_identifying_fields_to_string(self)

    def __hash__(self):
        return hash(f"{__name__}.{self.__class__.__name__}")

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = get_identifying_fields(self)
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
