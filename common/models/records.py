from __future__ import annotations

import re
from datetime import date
from typing import Any
from typing import Iterable
from typing import Optional

from django.db import models
from django.db.models import Case
from django.db.models import F
from django.db.models import Field
from django.db.models import Max
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models import When
from django.db.models.query_utils import DeferredAttribute
from django.db.transaction import atomic
from django.template import loader
from django.urls import NoReverseMatch
from django.urls import reverse
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet

from common import exceptions
from common import validators
from common.exceptions import IllegalSaveError
from common.exceptions import NoDescriptionError
from common.models import TimestampedMixin
from common.validators import UpdateType
from workbaskets.validators import WorkflowStatus


class TrackedModelQuerySet(PolymorphicQuerySet):
    def latest_approved(self) -> QuerySet:
        """
        Get all the latest versions of the model being queried which have been
        approved.

        This will specifically fetch the most recent approved row pertaining to an object.
        If a row is unapproved, or has subsequently been rejected after approval, it should
        not be included in the returned QuerySet. Likewise any objects which have never been
        approved (are in draft as an initial create step) should not appear in the queryset.
        Any row marked as deleted will also not be fetched.

        If done from the TrackedModel this will return the objects for all tracked models.
        """
        return self.filter(is_current__isnull=False).exclude(
            update_type=UpdateType.DELETE,
        )

    def approved_up_to_transaction(self, transaction=None) -> QuerySet:
        """
        Get the approved versions of the model being queried unless there exists
        a version of the model in a draft state within a transaction preceding
        (and including) the given transaction in the workbasket of the given
        transaction.

        The generated SQL is equivalent to:

        .. code:: SQL

            SELECT *,
                   Max(t3."id") filter (
                       WHERE (
                           t3."transaction_id" = {TRANSACTION_ID}
                        OR ("common_transaction"."order" < {TRANSACTION_ORDER} AND "common_transaction"."workbasket_id" = {WORKBASKET_ID})
                        OR ("workbaskets_workbasket"."approver_id" IS NOT NULL AND "workbaskets_workbasket"."status" IN (APPROVED_STATUSES))
                       )
                   ) AS "latest"
              FROM "common_trackedmodel"
             INNER JOIN "common_versiongroup"
                ON "common_trackedmodel"."version_group_id" = "common_versiongroup"."id"
              LEFT OUTER JOIN "common_trackedmodel" t3
                ON "common_versiongroup"."id" = t3."version_group_id"
              LEFT OUTER JOIN "common_transaction"
                ON t3."transaction_id" = "common_transaction"."id"
              LEFT OUTER JOIN "workbaskets_workbasket"
                ON "common_transaction"."workbasket_id" = "workbaskets_workbasket"."id"
             WHERE NOT "common_trackedmodel"."update_type" = 2
             GROUP BY "common_trackedmodel"."id"
            HAVING max(t3."id") filter (
                       WHERE (
                           t3."transaction_id" = {TRANSACTION_ID}
                        OR ("common_transaction"."order" < {TRANSACTION_ORDER} AND "common_transaction"."workbasket_id" = {WORKBASKET_ID})
                        OR ("workbaskets_workbasket"."approver_id" IS NOT NULL AND "workbaskets_workbasket"."status" IN (APPROVED_STATUSES))
                       )
            ) = "common_trackedmodel"."id"
        """
        if not transaction:
            return self.latest_approved()

        return (
            self.annotate(
                latest=Max(
                    "version_group__versions",
                    filter=(
                        Q(version_group__versions__transaction=transaction)
                        | Q(
                            version_group__versions__transaction__workbasket=transaction.workbasket,
                            version_group__versions__transaction__order__lt=transaction.order,
                        )
                        | self.approved_query_filter("version_group__versions__")
                    ),
                ),
            )
            .filter(latest=F("id"))
            .exclude(update_type=UpdateType.DELETE)
        )

    def latest_deleted(self) -> QuerySet:
        """
        Get all the latest versions of the model being queried which have been
        approved, but also deleted.

        See `latest_approved`.

        If done from the TrackedModel this will return the objects for all tracked models.
        """
        return self.filter(is_current__isnull=False, update_type=UpdateType.DELETE)

    def since_transaction(self, transaction_id: int) -> QuerySet:
        """
        Get all instances of an object since a certain transaction (i.e. since a
        particular workbasket was accepted).

        This will not include objects without a transaction ID - thus excluding rows which
        have not been accepted yet.

        If done from the TrackedModel this will return all objects from all transactions since
        the given transaction.
        """
        return self.filter(transaction__id__gt=transaction_id)

    def as_at(self, date: date) -> QuerySet:
        """
        Return the instances of the model that were represented at a particular
        date.

        If done from the TrackedModel this will return all instances of all
        tracked models as represented at a particular date.
        """
        return self.filter(valid_between__contains=date)

    def active(self) -> QuerySet:
        """
        Return the instances of the model that are represented at the current
        date.

        If done from the TrackedModel this will return all instances of all
        tracked models as represented at the current date.
        """
        return self.as_at(date.today())

    def get_versions(self, **kwargs) -> QuerySet:
        for field in self.model.identifying_fields:
            if field not in kwargs:
                raise exceptions.NoIdentifyingValuesGivenError(
                    f"Field {field} expected but not found.",
                )
        return self.filter(**kwargs)

    def get_latest_version(self, **kwargs):
        """Gets the latest version of a specific object."""
        return self.get_versions(**kwargs).latest_approved().get()

    def get_current_version(self, **kwargs):
        """Gets the current version of a specific object."""
        return self.get_versions(**kwargs).active().get()

    def get_first_version(self, **kwargs):
        """Get the original version of a specific object."""
        return self.get_versions(**kwargs).order_by("id").first()

    def excluding_versions_of(self, version_group):
        return self.exclude(version_group=version_group)

    def with_workbasket(self, workbasket):
        """Add the latest versions of objects from the specified workbasket."""

        if workbasket is None:
            return self

        query = Q()

        # get models in the workbasket
        in_workbasket = self.model.objects.filter(transaction__workbasket=workbasket)
        # add latest version of models from the current workbasket
        return self.filter(query) | in_workbasket

    def has_approved_state(self):
        """Get objects which have been approved/sent-to-cds/published."""

        return self.filter(self.approved_query_filter())

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

    def _get_current_related_lookups(
        self, model, *lookups, prefix="", recurse_level=0
    ) -> list[str]:
        """
        Build a list of lookups for the current versions of related objects.

        Many Tracked Models will have relationships to other Tracked Models through
        Foreign Keys. However as this system implements an append-only log, and
        Foreign Keys attach directly to a specific row, oftentimes relations will
        show objects which won't be the "current" or most recent version of that
        relation.

        Normally the most current version of a Tracked Model can be accessed through the
        models Version Group. This method builds up a list of related lookups which
        connects all of a models relations to their "current" version via their Version
        Group.
        """
        related_lookups = []
        for relation, _ in model.get_relations():
            if lookups and relation.name not in lookups:
                continue
            related_lookups.append(f"{prefix}{relation.name}")
            related_lookups.append(f"{prefix}{relation.name}__version_group")
            related_lookups.append(
                f"{prefix}{relation.name}__version_group__current_version",
            )

            if recurse_level:
                related_lookups.extend(
                    self._get_current_related_lookups(
                        model,
                        *lookups,
                        prefix=f"{prefix}{relation.name}__version_group__current_version__",
                        recurse_level=recurse_level - 1,
                    ),
                )
        return related_lookups

    def with_latest_links(self, *lookups, recurse_level=0) -> QuerySet:
        """
        Runs a `.select_related` operation for all relations, or given
        relations, joining them with the "current" version of the relation as
        defined by their Version Group.

        As many objects will often want to access the current version of a
        relation, instead of the actual linked object, this saves on having to
        run multiple queries for every current relation.
        """
        related_lookups = self._get_current_related_lookups(
            self.model, *lookups, recurse_level=recurse_level
        )
        return self.select_related(
            "version_group", "version_group__current_version", *related_lookups
        )

    def get_queryset(self):
        return self.annotate_record_codes().order_by("record_code", "subrecord_code")

    def approved_query_filter(self, prefix=""):
        return Q(
            **{
                f"{prefix}transaction__workbasket__status__in": WorkflowStatus.approved_statuses(),
                f"{prefix}transaction__workbasket__approver__isnull": False,
            }
        )

    @staticmethod
    def _when_model_record_codes():
        """
        Iterate all TrackedModel subclasses, generating When statements that map
        the model to its record_code.

        If any of the models start using a foreign key then this function will
        need to be updated.
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
        """Return F function or Value to fetch subrecord_code in a query."""
        if isinstance(model.subrecord_code, DeferredAttribute):
            return F(f"{model._meta.model_name}__subrecord_code")
        return Value(model.subrecord_code)

    @staticmethod
    def _when_model_subrecord_codes():
        """
        Iterate all TrackedModel subclasses, generating When statements that map
        the model to its subrecord_code.

        This function is a little more complex than when_model_record_codes as
        subrecord_code may be a standard class attribute or a ForeignKey.
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


class VersionGroup(TimestampedMixin):
    current_version = models.OneToOneField(
        "common.TrackedModel",
        on_delete=models.SET_NULL,
        null=True,
        related_query_name="is_current",
    )


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

    objects = PolymorphicManager.from_queryset(TrackedModelQuerySet)()

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
    (Note that because mutliple versions of each model will exist this does not
    actually equate to a ``UNIQUE`` constraint in the database.)
    """

    taric_template = None

    def get_taric_template(self):
        """
        Generate a TARIC XML template name for the given class.

        Any TrackedModel must be representable via a TARIC compatible XML
        record.
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
                "template.",
            ) from e

        return template_name

    def new_draft(self, workbasket, save=True, **kwargs):
        cls = self.__class__

        new_object_kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name
            not in (
                self._meta.pk.name,
                "transaction",
                "polymorphic_ctype",
                "trackedmodel_ptr",
                "id",
            )
        }

        new_object_kwargs["update_type"] = validators.UpdateType.UPDATE
        new_object_kwargs.update(kwargs)

        if "transaction" not in new_object_kwargs:
            # Only create a transaction if the user didn't specify one.
            new_object_kwargs["transaction"] = workbasket.new_transaction()

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

        return new_object

    def get_versions(self):
        if hasattr(self, "version_group"):
            return self.version_group.versions.all()
        query = Q(**self.get_identifying_fields())
        return self.__class__.objects.filter(query)

    def get_description(self):
        return self.get_descriptions().last()

    def get_descriptions(self, transaction=None) -> TrackedModelQuerySet:
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

        for field, model in descriptions_model.get_relations():
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
            "valid_between",
        )

        if transaction:
            return query.approved_up_to_transaction(transaction=transaction)

        return query.latest_approved()

    def identifying_fields_unique(
        self,
        identifying_fields: Optional[Iterable[str]] = None,
    ) -> bool:
        return (
            self.__class__.objects.filter(
                **self.get_identifying_fields(identifying_fields)
            )
            .latest_approved()
            .count()
            <= 1
        )

    def identifying_fields_to_string(
        self,
        identifying_fields: Optional[Iterable[str]] = None,
    ) -> str:
        field_list = [
            f"{field}={str(value)}"
            for field, value in self.get_identifying_fields(identifying_fields).items()
        ]

        return ", ".join(field_list)

    def _get_version_group(self) -> VersionGroup:
        if self.update_type == validators.UpdateType.CREATE:
            return VersionGroup.objects.create()
        return self.get_versions().latest_approved().last().version_group

    def _can_write(self):
        return not (
            self.pk
            and self.transaction.workbasket.status in WorkflowStatus.approved_statuses()
        )

    def get_identifying_fields(
        self,
        identifying_fields: Optional[Iterable[str]] = None,
    ) -> dict[str, Any]:
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

    @property
    def structure_code(self):
        return str(self)

    @property
    def structure_description(self):
        description = None
        if hasattr(self, "descriptions"):
            description = self.get_descriptions().last()
            if description:
                # Get the actual description, not just the object
                description = description.description
        if hasattr(self, "description"):
            description = self.description
        return description or "-"

    @property
    def current_version(self) -> TrackedModel:
        current_version = self.version_group.current_version
        if current_version is None:
            raise self.__class__.DoesNotExist("Object has no current version")
        return current_version

    @classmethod
    def get_relations(cls) -> list[tuple[Field, type[TrackedModel]]]:
        """Find all foreign key and one-to-one relations on an object and return
        a list containing tuples of the field instance and the related model it
        links to."""
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
        Add the ability to get the current instance of a related object through
        an attribute. For example if a model is like so:

        .. code:: python
            class ExampleModel(TrackedModel):
                # must be a TrackedModel
                other_model = models.ForeignKey(OtherModel, on_delete=models.PROTECT)

        The latest version of the relation can be accessed via:

        .. code:: python
            example_model = ExampleModel.objects.first()
            example_model.other_model_current  # Gets the latest version
        """

        if item.endswith("_current"):
            field_name = item[:-8]
            if field_name in [field.name for field, _ in self.get_relations()]:
                return getattr(self, field_name).current_version

        return self.__getattribute__(item)

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

        return return_value

    def __str__(self):
        return ", ".join(
            f"{field}={getattr(self, field, None)}" for field in self.identifying_fields
        )

    def __hash__(self):
        return hash(f"{__name__}.{self.__class__.__name__}")

    def get_url(self, action="detail"):
        kwargs = {}
        if action != "list":
            kwargs = self.get_identifying_fields()
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
