from __future__ import annotations

from typing import List

from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import Max
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.db.models.query_utils import DeferredAttribute
from django_cte import CTEQuerySet
from polymorphic.query import PolymorphicQuerySet

from common import exceptions
from common.models.tracked_utils import get_models_linked_to
from common.models.utils import LazyTransaction
from common.models.utils import get_current_transaction
from common.querysets import TransactionPartitionQuerySet
from common.querysets import ValidityQuerySet
from common.validators import UpdateType


class TrackedModelQuerySet(
    PolymorphicQuerySet,
    CTEQuerySet,
    ValidityQuerySet,
    TransactionPartitionQuerySet,
):
    def latest_approved(self) -> TrackedModelQuerySet:
        """
        Get all the latest versions of the model being queried which have been
        approved.

        This will specifically fetch the most recent approved row pertaining to
        an object. If a row is unapproved, or has subsequently been rejected
        after approval, it should not be included in the returned QuerySet.
        Likewise any objects which have never been approved (are in draft as an
        initial create step) should not appear in the queryset. Any row marked
        as deleted will also not be fetched. If done from the TrackedModel this
        will return the objects for all tracked models.
        """
        return self.filter(is_current__isnull=False).exclude(
            update_type=UpdateType.DELETE,
        )

    def current(self) -> TrackedModelQuerySet:
        """
        Get the approved versions of the model or the latest draft versions, if
        they exist within a transaction preceding (and including) the given
        transaction.

        The 'current' transaction is obtained from the globally  available
        current transaction - see the common.models.utils module for details of
        how this is managed.
        """
        return self.approved_up_to_transaction(
            LazyTransaction(get_value=get_current_transaction),
        )

    def approved_up_to_transaction(self, transaction=None) -> TrackedModelQuerySet:
        """Get the approved versions of the model being queried, unless there
        exists a version of the model in a draft state within a transaction
        preceding (and including) the given transaction in the workbasket of the
        given transaction."""
        if not transaction:
            return self.latest_approved()

        return (
            self.annotate(
                latest=Max(
                    "version_group__versions",
                    filter=self.as_at_transaction_filter(
                        transaction,
                        "version_group__versions__",
                    ),
                ),
            )
            .filter(latest=F("id"))
            .exclude(update_type=UpdateType.DELETE)
        )

    def latest_deleted(self) -> TrackedModelQuerySet:
        """
        Get all the latest versions of the model being queried which have been
        approved, but also deleted.

        See `latest_approved`. If done from the TrackedModel this will return
        the objects for all tracked models.
        """
        return self.filter(is_current__isnull=False, update_type=UpdateType.DELETE)

    def versions_up_to(self, transaction) -> TrackedModelQuerySet:
        """
        Get all versions of an object up until and including the passed
        transaction.

        If the transaction is in a draft workbasket, this will include all of
        the approved transactions and any before it in the workbasket. This is
        similar to `approved_up_to_transaction` except it includes all versions,
        not just the most recent.
        """
        return self.filter(
            self.as_at_transaction_filter(transaction),
        ).version_ordering()

    def get_versions(self, **kwargs) -> TrackedModelQuerySet:
        for field in self.model.identifying_fields:
            if field not in kwargs:
                raise exceptions.NoIdentifyingValuesGivenError(
                    f"Field {field} expected but not found.",
                )
        return self.filter(**kwargs).version_ordering()

    def get_latest_version(self, **kwargs):
        """Gets the latest version of a specific object."""
        return self.get_versions(**kwargs).latest_approved().get()

    def get_first_version(self, **kwargs):
        """Get the original version of a specific object."""
        return self.get_versions(**kwargs).first()

    def excluding_versions_of(self, version_group):
        """
        Exclude results which have the specified version_group.

        :param version_group VersionGroup: Exclude the members of this version group
        :rtype QuerySet:
        """
        return self.exclude(version_group=version_group)

    def has_approved_state(self):
        """Get objects which have been approved/sent-to-cds/published."""
        return self.filter(self.approved_query_filter())

    def annotate_record_codes(self) -> TrackedModelQuerySet:
        """
        Annotate results with TARIC Record code and Subrecord code.

        :return: Query annotated with record_code and subrecord_code.
        """
        # Generates case statements to do the mapping from model to record_code and subrecord_code.
        return self.annotate(
            record_code=Case(
                *(TrackedModelQuerySet._when_model_record_codes()),
                output_field=CharField(),
            ),
            subrecord_code=Case(
                *(TrackedModelQuerySet._when_model_subrecord_codes()),
                output_field=CharField(),
            ),
        )

    def version_ordering(self) -> TrackedModelQuerySet:
        """
        Returns objects in canonical order, i.e. by the order in which they
        appear in transactions.

        For querysets that only contain the "latest" version of a model, this
        will return the objects in the order that the most recent version was
        added.

        For querysets that contain multiple versions of a model, this will
        return the objects in the order those versions were added. I.e,
        subsequently calling `first()` always selects the first version and
        `last()` selects the most recent version (contained in the queryset).
        """
        return self.order_by("transaction__partition", "transaction__order")

    def _get_current_related_lookups(
        self, model, *lookups, prefix="", recurse_level=0
    ) -> List[str]:
        """
        Build a list of lookups for the current versions of related objects.

        Many Tracked Models will have relationships to other Tracked Models
        through Foreign Keys. However as this system implements an append-only
        log, and Foreign Keys attach directly to a specific row, oftentimes
        relations will show objects which won't be the "current" or most recent
        version of that relation. Normally the most current version of a Tracked
        Model can be accessed through the models Version Group. This method
        builds up a list of related lookups which connects all of a models
        relations to their "current" version via their Version Group.
        """
        related_lookups = []
        for relation in get_models_linked_to(model).keys():
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

    def with_latest_links(self, *lookups, recurse_level=0) -> TrackedModelQuerySet:
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

    @staticmethod
    def _when_model_record_codes():
        """
        Iterate all TrackedModel subclasses, generating When statements that map
        the model to its record_code.

        If any of the models start using a foreign key then this function will
        need to be updated.
        """
        from common.models.trackedmodel import TrackedModel

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
        from common.models.trackedmodel import TrackedModel

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

    def with_workbasket(self, workbasket):
        """Add the latest versions of objects from the specified workbasket."""

        if workbasket is None:
            return self

        query = Q()

        # get models in the workbasket
        in_workbasket = self.model.objects.filter(transaction__workbasket=workbasket)
        # add latest version of models from the current workbasket
        return self.filter(query) | in_workbasket
