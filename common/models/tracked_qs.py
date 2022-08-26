from __future__ import annotations

from hashlib import sha256
from typing import List

from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import Max
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.db.models.fields import Field
from django.db.models.query_utils import DeferredAttribute
from django_cte import CTEQuerySet
from polymorphic.query import PolymorphicQuerySet

from common import exceptions
from common.models.tracked_utils import get_models_linked_to
from common.models.utils import LazyTransaction
from common.models.utils import get_current_transaction
from common.querysets import TransactionPartitionQuerySet
from common.querysets import ValidityQuerySet
from common.util import resolve_path
from common.validators import UpdateType

PK_INTERVAL_CHUNK_SIZE = 1024 * 64
"""Default chunk size for primary key intervals, see: `as_pk_intervals.`"""


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
        Returns a queryset of approved versions of the model up to the globally
        defined current transaction (see ``common.models.utils`` for details of
        how this is managed).

        If this method is called from within a running instance of the Django
        web application (i.e. application middleware has been exectuted), then
        TransactionMiddleware will automatically set the globally defined,
        current transaction to the current transaction in the global Workbasket.

        Otherwise, if TransactionMiddleware has not been executed (for
        instance, when running from the shell / Jupyter), then care must be
        taken to ensure the global current transaction is set up correctly
        (see ``set_current_transaction()`` and ``override_current_transaction()``
        in ``common.models.utils``).
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

    def record_ordering(self) -> TrackedModelQuerySet:
        """
        Returns objects in order of their TARIC record code and subrecord code.

        This is primarily useful for querysets that contain multiple types of
        tracked model, e.g. when exporting the tracked models to XML.
        """
        return self.annotate_record_codes().order_by(
            "transaction__partition",
            "transaction__order",
            "record_code",
            "subrecord_code",
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

    def follow_path(self, path: str) -> TrackedModelQuerySet:
        """
        Returns a queryset filled with objects that are found by following the
        passed path.

        At each stage of the path, only the current versions of each object are
        considered, so that upon reaching the end of the path the queryset will
        only contain current versions that are linked back to the start of the
        path by current versions as well.

        E.g. ``follow_path(Measure.objects.filter(…), 'measurecomponent')`` will
        return a queryset that contains all the measure components that are
        attached to the filtered measures, as of the current() transaction.
        """
        steps = resolve_path(self.model, path)

        qs = self
        for model_type, rel in steps:
            if isinstance(rel, Field):
                # The foreign key is on the model we are moving towards. So we
                # follow the foreign key on that model and filter by the current
                # model's version group.
                values = set(qs.values_list("version_group_id", flat=True))
                filter = f"{rel.name}__version_group_id__in"
            else:
                # The foreign key is on the model we are moving away from. So we
                # resolve the foreign key into the version group that we are
                # looking for.
                values = set(
                    qs.values_list(
                        f"{rel.remote_field.name}__version_group_id",
                        flat=True,
                    ),
                )
                filter = "version_group_id__in"

            if any(values):
                qs = model_type.objects.current().filter(**{filter: values})
            else:
                qs = model_type.objects.none()

        return qs.distinct()

    def as_pk_intervals(self, chunk_size=PK_INTERVAL_CHUNK_SIZE):
        """
        Given a sequence of primary keys, return interval tuples
        of: ((first_pk, last_pk), ...)

        By default[1] this provides a much smaller wire format, than, for instance sending all primary keys, thus being sutable for use in Celery.
        In the happy case, a single interval will be returned, but in the case of a large number of primary keys, multiple intervals will be returned - determined by chunk_size, gaps in the original data set will also generate more intervals.  Gaps may be generated when users delete items workbaskets.


        Chunking is provided to make it easy to chunk up data for consumers of this data (e.g. a celery task on the other end).

        Unscientifically testing this on a developers' laptop with the seed workbasket (pk=1) with > 9m models, this takes 9.2 seconds, to generate 3426 interval pairs, with 128kb chunks this generates 3430 pairs.

        [1]  Under a pathological case, where every primary key iterated by more than one, this would be worse.
        """
        qs = self
        if qs.query.order_by != ("pk",):
            qs = self.order_by("pk")

        pks = qs.values_list("pk", flat=True)

        model_iterator = iter(pks)

        try:
            pk = next(model_iterator)
        except StopIteration:
            return

        first_pk = pk
        item_count = 0
        try:
            while True:
                item_count += 1
                last_pk = pk
                pk = next(model_iterator)
                if (item_count > chunk_size) or (pk > last_pk + 1):
                    # Yield an interval tuple of (first_pk, last_pk) if the amount of items is more than the chunk size,
                    # or if the pks are not contiguous.
                    yield first_pk, last_pk
                    first_pk = pk
                    item_count = 0
        except StopIteration:
            pass

        yield first_pk, pk

    def from_pk_intervals(self, *pk_intervals):
        """
        Returns a queryset of TrackedModel objects that match the primary key
        tuples, (start, end)

        To generate data in this format call as_pk_ranges on a queryset.
        """
        q = Q()
        for first_pk, last_pk in pk_intervals:
            q |= Q(pk__gte=first_pk, pk__lte=last_pk)

        if not q:
            # An empty filter would match everything, so return an empty queryset in that case.
            return self.none()

        return self.filter(q)

    @classmethod
    def _content_hash(cls, models):
        """
        Implementation of content hashing, shared by content_hash and
        content_hash_fast, should not be called directly, instead `content_hash`
        or `content_hash_fast` should be called which impose order on the
        models.

        Code is shared in this private method so the naive and fast
        implementations return the same hash.
        """
        sha = sha256()
        for o in models:
            sha.update(o.content_hash().digest())
        return sha

    def content_hash(self):
        """
        :return: Combined sha256 hash for all contained TrackedModels.

        Ordering is by TrackedModel primary key, so the hash will be stable across multiple queries.
        """
        return self._content_hash(self.order_by("pk").iterator())

    # def group_by_type(self):
    #     """Yield a sequence of query sets, where each queryset contains only one
    #     Polymorphic ctype, enabling the use of prefetch and select_related on
    #     them."""
    #     pks = self.values_list("pk", flat=True)
    #     polymorphic_ctypes = (
    #         self.non_polymorphic()
    #         .only("polymorphic_ctype_id")
    #         .distinct("polymorphic_ctype_id")
    #         .values_list("polymorphic_ctype_id", flat=True)
    #     )
    #
    #     for polymorphic_ctype in polymorphic_ctypes:
    #         # Query contenttypes to get the concrete class instance
    #         klass = ContentType.objects.get_for_id(polymorphic_ctype).model_class()
    #         yield klass.objects.filter(pk__in=pks)
    #
    # def select_related_copyable_fields(self):
    #     """Split models into separate querysets, using group_by_type and call
    #     select_related on any related fields found in the `copyable_fields`
    #     attribute."""
    #     pks = self.values_list("pk", flat=True)
    #     for qs in self.group_by_type():
    #         # Work out which fields from copyable_fields may be use in select_related
    #         related_fields = [
    #             field.name
    #             for field in qs.model.copyable_fields
    #             if hasattr(field, "related_query_name")
    #         ]
    #         yield qs.select_related(*related_fields).filter(pk__in=pks)
    #
    # def content_hash_fast(self):
    #     """
    #     Use `select_related_copyable_fields` to call select_related on fields
    #     that will be hashed.
    #
    #     This increases the speed a little more than 2x, at the expense of keeping the data in memory.
    #     On this developers' laptop 2.3 seconds vs 6.5 for the naive implementation in `content_hash`,
    #     for larger amounts of data the difference got bigger, 23 seconds vs 90, though this may
    #     because more types of data were represented.
    #
    #     For larger workbaskets batching should be used to keep memory usage withing reasonable bounds.
    #
    #     The hash value returned here should be the same as that from `content_hash`.
    #     """
    #     # Fetch data using select_related, at this point the ordering
    #     # will have been lost.
    #     all_models = chain(*self.select_related_copyable_fields())
    #
    #     # Sort the data using trackedmodel_ptr_id, since the previous step outputs
    #     # an iterable, sorted is used, instead of order_by on a queryset.
    #     sorted_models = sorted(all_models, key=lambda o: o.trackedmodel_ptr_id)
    #     return self._content_hash(sorted_models)
