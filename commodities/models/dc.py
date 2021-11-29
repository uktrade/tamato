"""Includes dataclasses used in goods nomenclature hierarchy tree management."""
from __future__ import annotations

import logging
from copy import copy
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from itertools import groupby
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import Union

from django.db.models import Q

from commodities import business_rules as cbr
from commodities.models.constants import SUFFIX_DECLARABLE
from commodities.models.constants import TreeNodeRelation
from commodities.models.orm import CommodityCode
from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from commodities.models.orm import GoodsNomenclature
from commodities.models.orm import GoodsNomenclatureIndent
from commodities.util import clean_item_id
from commodities.util import contained_date_range
from commodities.util import date_ranges_overlap
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.models.constants import ClockType
from common.models.dc.base import BaseModel
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.util import TaricDateRange
from common.util import get_latest_versions
from common.validators import UpdateType
from importer.namespaces import TARIC_RECORD_GROUPS
from measures import business_rules as mbr
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.querysets import MeasuresQuerySet
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

__all__ = [
    "Commodity",
    "CommodityChange",
    "CommodityChangeRecordLoader",
    "CommodityCollection",
    "CommodityCollectionLoader",
    "CommodityTreeSnapshot",
    "TrackedModelReflection",
]

TTrackedModelIdentifier = Union[str, int]

COMMODITY_RECORD_ATTRIBUTES: dict[str, tuple[str, str]] = {
    "40000": ("goods_nomenclature", "item_id"),
    "40005": ("goods_nomenclature_indent", "indented_goods_nomenclature__item_id"),
    "40010": (
        "goods_nomenclature_description_period",
        "described_goods_nomenclature__item_id",
    ),
    "40015": (
        "goods_nomenclature_description",
        "described_goods_nomenclature__item_id",
    ),
    "40020": ("footnote_association_goods_nomenclature", "goods_nomenclature__item_id"),
    "40035": ("goods_nomenclature_origin", "new_goods_nomenclature__item_id"),
    "40040": ("goods_nomenclature_successor", "replaced_goods_nomenclature__item_id"),
}

PREEMPTIVE_TRANSACTION_SEED = -int(1e5)

TRACKEDMODEL_IDENTIFIER_KEYS = {
    "additional_codes.AdditionalCode": "code",
    "commodities.GoodsNomenclature": "item_id",
    "commodities.GoodsNomenclatureIndentNode": "depth",
    "geo_areas.GeographicalArea": "area_id",
    "measures.MeasureAction": "code",
    "measures.MeasureConditionCode": "code",
    "measures.MeasurementUnit": "code",
    "measures.MeasurementUnitQualifier": "code",
    "measures.MonetaryUnit": "code",
    "quotas.QuotaOrderNumber": "order_number",
    "regulations.Group": "group_id",
}

TRACKEDMODEL_IDENTIFIER_FALLBACK_KEY = TrackedModel.identifying_fields[0]
TRACKEDMODEL_PRIMARY_KEY = "pk"


@dataclass
class Commodity(BaseModel):
    """Provides a wrapper of the GoodsNomenclature model."""

    obj: GoodsNomenclature = None
    item_id: Optional[str] = None
    suffix: Optional[str] = None
    indent: Optional[int] = None
    valid_between: Optional[TaricDateRange] = None

    def get_item_id(self) -> Optional[str]:
        """Returns the item_id attribute if set, or the object item_id field
        otherwise."""
        if self.item_id is not None:
            return self.item_id

        if self.obj is None:
            return

        return self.obj.item_id

    def get_suffix(self) -> Optional[str]:
        """Returns the suffix attribute if set, or the object suffix field
        otherwise."""
        if self.suffix is not None:
            return self.suffix

        if self.obj is None:
            return

        return self.obj.suffix

    def get_indent(self) -> Optional[int]:
        """Returns the indent attribute if set, or the object item_id field
        otherwise."""
        if self.indent is not None:
            return self.indent

        if self.obj is None:
            return

        obj = (
            GoodsNomenclatureIndent.objects.latest_approved()
            .filter(
                indented_goods_nomenclature__item_id=self.get_item_id(),
            )
            .order_by("transaction_id")
            .last()
        )

        if obj is None:
            return

        return int(obj.indent)

    def get_valid_between(self) -> TaricDateRange:
        """Returns the validity period for the commodity."""
        if self.valid_between is not None:
            return self.valid_between

        if self.obj is None:
            return

        return self.obj.valid_between

    @property
    def code(self) -> CommodityCode:
        """Returns the the commodity code."""
        return CommodityCode(code=self.get_item_id())

    @property
    def description(self) -> Optional[str]:
        """Returns the description of the commodity."""
        if self.obj is None:
            return
        return self.obj.get_description().description

    @property
    def start_date(self) -> date:
        """Returns the validity start date of the commodity."""
        return self.obj.valid_between.lower

    @property
    def end_date(self) -> Optional[date]:
        """Returns the validity end date of the commodity."""
        return self.obj.valid_between.upper

    @property
    def identifier(self) -> str:
        """Returns an override of the model instance identifier property."""
        code = self.code.dot_code
        extra = f"{self.get_suffix()}-{self.get_indent()}/{self.version}"
        return f"{code}-{extra}"

    @property
    def good(self) -> Optional[TrackedModelReflection]:
        if self.obj is None:
            return

        overrides = {
            attr: getattr(self, attr)
            for attr in self.get_field_names(exclude=["obj", "indent"])
            if getattr(self, attr) is not None
        }

        return get_tracked_model_reflection(self.obj, **overrides)

    @property
    def version(self) -> int:
        """
        Returns the version of the object.

        TrackedModel objects support version control. The version_group field
        holds pointers to all prior and current versions of a Taric record. The
        versions are ordered based on transaction id. This method returns the
        version number of the object based on the place of its transaction id in
        the version transaction ids sequence.
        """
        transaction_orders = self._get_transaction_orders()
        version = transaction_orders.index(self.obj.transaction.order) + 1
        return version

    @property
    def current_version(self) -> int:
        """Returns the current version of the Taric record."""
        return self.obj.version_group.versions.count()

    @property
    def is_current_version(self) -> bool:
        """Returns True if this is the current version of the Taric record."""
        return self.obj == self.obj.current_version

    def _get_transaction_ids(self) -> tuple[int]:
        """Returns the id-s of all transactions in the version group of the
        record."""
        transaction_ids = self.obj.version_group.versions.values_list(
            "transaction_id",
            flat=True,
        )
        return tuple(transaction_ids)

    def _get_transaction_orders(self) -> tuple[int]:
        """Returns the id-s of all transactions in the version group of the
        record."""
        transaction_orders = self.obj.version_group.versions.values_list(
            "transaction__order",
            flat=True,
        )
        return tuple(transaction_orders)

    def _get_transactions(self) -> tuple[int]:
        """Returns the id-s of all transactions in the version group of the
        record."""
        transaction_orders = self.obj.version_group.versions.values_list(
            "transaction",
            flat=True,
        )
        return tuple(transaction_orders)

    def __eq__(self, commodity: "Commodity") -> bool:
        """
        Returns true if the two commodities are equal.

        The two commodities are considered equal if they share the same code,
        suffix, indent, version, and validity dates.
        """
        if commodity is None:
            return False

        return (
            self.identifier == commodity.identifier
            and self.get_valid_between() == commodity.get_valid_between()
        )

    def __str__(self) -> str:
        """Returns a string representation of the commodity."""
        return self._get_repr(self.identifier)

    def __repr__(self) -> str:
        """Overrides the __repr__ method of the dataclass."""
        return self._get_repr(self.identifier)


@dataclass
class CommodityTreeBase(BaseModel):
    """
    Provides a base model for commodity tree and snapshots.

    See the docs of CommodityTree and CommodityTreeSnapshot for details.
    """

    commodities: List[Commodity]

    def get_commodity(
        self,
        code: str,
        suffix: Optional[str] = None,
        version: Optional[int] = None,
        version_group_id: Optional[int] = None,
    ) -> Optional[Commodity]:
        """
        Returns a commodity matching the provided arguments, if found.

        The commodity code can be provided any of the following formats
        (see Commodity dataclass for more details):
        - GoodsNomenclature.item_id field format (e.g. '0101201000')
        - Dot-format (e.g. '0101.20.10.00')
        - Trimmed format (e.g. '01012010')
        - Trimmed dot-format (e.g. '0101.20.10')

        The method supports search by code only:
        - the suffix will default to '80';
        - the version will default to the current version of the related GoodsNomenclature object;
        - the version_group_id argument will not figure in the search if it is not specified.
        """
        code = clean_item_id(code)

        suffix = suffix or SUFFIX_DECLARABLE

        try:
            return next(
                filter(
                    lambda x: (
                        x.code.code == code
                        and x.get_suffix() == suffix
                        and x.version == (version or x.current_version)
                        and (
                            version_group_id is None
                            or version_group_id == x.obj.version_group.id
                        )
                    ),
                    self.commodities,
                ),
            )
        except StopIteration:
            return None

    @property
    def max_transaction(self) -> Optional[Transaction]:
        version_groups = (
            commodity.obj.version_group
            for commodity in self.commodities
            if commodity.obj
        )

        return (
            Transaction.objects.filter(
                tracked_models__version_group__in=version_groups,
            )
            .order_by("order")
            .last()
        )


@dataclass
class SnapshotDiff(BaseModel):
    """
    Provides a construct for CommodityTreeSnapshot diffs.

    The diff construct provides a diff per commodity and relation.
    That is, you can compare across two commodity tree snapshots
    the ancestors, parents, siblings, or children of a given commodity
    and find out how they changed between the two snapshots.

    2. Use-Case Scenarios for SnapshotDiffs
    There can be a two motivations for getting a diff between snapshots:
    - compare where a commodity sits in the tree hierarchy
      at two different points in time or as of two different transactions
    - compare the 'before' and 'after' snapshots around a tree update

    For additional context on on snapshots, see the docs for CommodityTreeSnapshot.
    """

    commodity: Commodity
    relation: TreeNodeRelation
    values: List[Union[Commodity, List[Commodity]]]

    @property
    def diff(self) -> List[Commodity]:
        """Returns the diff between the commodity relations across the two
        snapshots."""
        values = [
            [value] if isinstance(value, Commodity) or value is None else value
            for value in self.values
        ]

        diff = [
            value
            for value in (values[0] or []) + (values[1] or [])
            if value is not None
            if value not in values[0] or value not in values[1]
        ]

        return diff


@dataclass
class SnapshotMoment:
    """
    Provides a model for snapshot moments.

    The attributes of a moment are:
    - transaction: the up-to transaction for snapshot models (required)
    - date: a date on which all models in the snapshot must be effective (optional)
    """

    transaction: Transaction
    date: Optional[date] = None

    @property
    def order(self) -> int:
        """Returns the moment's transaction order."""
        return self.transaction.order

    @property
    def partition(self) -> TransactionPartition:
        return self.transaction.partition

    @property
    def clock_type(self):
        """Returns the clock type of the moment."""
        if self.date:
            return ClockType.COMBINED
        return ClockType.TRANSACTION


@dataclass
class CommodityTreeSnapshot(CommodityTreeBase):
    """
    Provides a model for commodity tree snapshots.

    CommodityTreeSnapshot builds a hierarchical tree
    based on the provided collection of commodities.
    See the docs to the __post_init__ method of this dataclass
    for details on the related business logic.

    NOTES:
    1. Calendar vs Transaction Clocks:
    The tariff database uses at least two "clocks":
    - the calendar clock, which revolves around validity dates
    - the transaction clock, which revolves around transaction ids

    A commodity tree snapshot can be taken using
    the calendar or transaction clock, or both.
    Accordingly the moments field of this dataclass is a tuple of:
    - an optional calendar date (when the clock type has a calendar)
    - an optional transaction id (when the clock type has a transaction)

    For additional context on commodity trees, see the docs for CommodityTree.
    """

    moment: SnapshotMoment
    commodities: List[Commodity]
    edges: Optional[Dict[str, Commodity]] = None

    def __post_init__(self) -> None:
        """
        Builds the commodity tree upon instantiation.

        The business logic for building the tree is as follows:
        - for the commodities first, and then traverse the sorted collection to build the tree
        - the _sort method is responsible for sorting logic, see its docs for details
        - the _traverse method is responsible for traversal, see its docs for details
        1. The commodity collection is first sorted on code, suffix and indent.
        Note that since this is a commodity tree snapshot,
        multiple versions of the same commodity are not possible.
        - this is the responsibility of the _sort method of this class
        2. Traversal of the sorted commodity collection is trivial:
        - the method keeps a running tally of the latest sorted commodity for a given indent
        - the parent of a commodity is the current object at (indent - 1)
        - the behaviour differs for 0-indent commodities:
          -- the method keeps a list of the prior sorted commodities
          -- this allows it to assign the correct parents for 0-indent headings.
        """
        chapters = {c.code.chapter for c in self.commodities}

        if len(chapters) > 1:
            msg = "All commodities in a group must be from the same HS chapter."
            raise CommodityTreeSnapshotException(msg)

        if len(chapters) > 1:
            raise ValueError(
                "All commodities in a group must be from the same HS chapter.",
            )

        self._sort()
        self._traverse()

        super().__post_init__()

    def get_parent(self, commodity: Commodity) -> Optional[Commodity]:
        """Returns the parent of a commodity in the snapshot tree."""
        try:
            return self.edges[commodity.identifier]
        except KeyError:
            return

    def get_siblings(self, commodity: Commodity) -> List[Commodity]:
        """Returns the siblings of a commodity in the snapshot tree."""
        parent = self.get_parent(commodity)

        if parent is None and commodity.is_chapter is True:
            return []

        return [
            c
            for c in self.commodities
            if c != commodity
            if self.get_parent(c) == parent
        ]

    def get_children(self, commodity: Commodity) -> List[Commodity]:
        """Returns the children of a commodity in the snapshot tree."""
        return [c for c in self.commodities if self.get_parent(c) == commodity]

    def get_ancestors(self, commodity: Commodity) -> List[Commodity]:
        """Returns all ancestors of a commodity in the snapshot tree."""
        try:
            return self.ancestors[commodity.identifier]
        except KeyError:
            return []

    def get_descendants(self, commodity: Commodity) -> List[Commodity]:
        """Returns all descendants of a commodity in the snapshot tree."""
        try:
            return self.descendants[commodity.identifier]
        except KeyError:
            return []

    def get_dependent_measures(
        self,
        commodity: Commodity,
        as_at: Optional[date] = None,
    ) -> MeasuresQuerySet:
        if commodity not in self.commodities:
            logger.warning(f"Commodity {commodity} not found in this snapshot.")
            return Measure.objects.none()

        qs = Measure.objects.filter(
            goods_nomenclature__item_id=commodity.get_item_id(),
            goods_nomenclature__suffix=commodity.get_suffix(),
        )

        if self.moment.clock_type == ClockType.TRANSACTION:
            qs = qs.approved_up_to_transaction(self.moment.transaction)
        else:
            qs = qs.latest_approved()

        if self.moment.clock_type == ClockType.COMBINED:
            qs = qs.with_effective_valid_between().filter(
                db_effective_valid_between__contains=self.moment.date,
            )
        elif as_at is not None:
            qs = qs.with_effective_valid_between().filter(
                Q(db_effective_valid_between__contains=as_at)
                | Q(valid_between__startswith__gte=as_at),
            )

        return qs

    def is_declarable(self, commodity: Commodity) -> bool:
        if commodity.get_suffix() != SUFFIX_DECLARABLE:
            return False

        return len(self.get_children(commodity)) == 0

    def compare_parents(
        self,
        commodity: Commodity,
        snapshot: CommodityTreeSnapshot,
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.PARENT)

    def compare_siblings(
        self,
        commodity: Commodity,
        snapshot: CommodityTreeSnapshot,
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.SIBLINGS)

    def compare_children(
        self,
        commodity: Commodity,
        snapshot: CommodityTreeSnapshot,
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.CHILDREN)

    def compare_ancestors(
        self,
        commodity: Commodity,
        snapshot: CommodityTreeSnapshot,
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.ANCESTORS)

    def compare_descendants(
        self,
        commodity: Commodity,
        snapshot: CommodityTreeSnapshot,
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.DESCENDANTS)

    def _sort(self) -> None:
        """
        Sorts the commodity collection to prepare it for traversal.

        NOTE: This methods is invoked by __post_init__ and should not be called directly.

        The commodity collection is sorted on code, suffix and indent.
        Note that since this is a commodity tree snapshot,
        multiple versions of the same commodity are not possible.
        """
        self.commodities = sorted(
            self.commodities,
            key=lambda x: (
                str(x.code),
                x.get_suffix(),
                x.get_indent(),
            ),
        )

    def _traverse(self):
        """
        Builds the commodity tree hierarchy.

        NOTE: This methods is invoked by __post_init__ and should not be called directly.

        Traversal of the sorted commodity collection works as follows:
        - the method keeps a running tally of the latest sorted commodity for a given indent
        - the parent of a commodity is the current object at (indent - 1)
        - the behaviour differs for 0-indent commodities:
          -- the method keeps a list of the prior sorted commodities
          -- this enables assignment of the correct parents for 0-indent headings.
        """
        indents = [[]]
        edges = {}
        ancestors = {}
        descendants = {}

        for commodity in self.commodities:
            indent = commodity.get_indent()

            # When we import commodity changes, e.g. from EU taric files
            # and a new commodity is created, we may not now its indent yet.
            if indent is None:
                continue

            if indent == 0:
                if not indents[0]:
                    parent = None
                else:
                    try:
                        parent = [
                            c
                            for c in indents[0]
                            if c.get_suffix() < commodity.get_suffix()
                        ][-1]
                    except IndexError:
                        parent = indents[0][0]
            elif indent == 1:
                try:
                    parent = indents[0][-1]
                except IndexError:
                    parent = None
            else:
                try:
                    parent = indents[:indent][-1]
                    # the case where we're using the 0-indent for the parent
                    if isinstance(parent, list):
                        parent = parent[0]
                except IndexError:
                    parent = None

            edges[commodity.identifier] = parent

            if indent == 0:
                indents[indent].append(commodity)
                indents = indents[: indent + 1]
            else:
                try:
                    indents[indent] = commodity
                    indents = indents[: indent + 1]
                except IndexError:
                    indents.append(commodity)

            commodities = indents[1:indent]
            parent = commodities[0] if commodities else commodity

            while True:
                try:
                    parent = edges[parent.identifier]
                except IndexError:
                    break
                if parent is None:
                    break
                commodities.insert(0, parent)

            ancestors[commodity.identifier] = commodities

            for ancestor in commodities:
                try:
                    descendants[ancestor.identifier].append(commodity)
                except KeyError:
                    descendants[ancestor.identifier] = [commodity]

        self.edges = edges
        self.ancestors = ancestors
        self.descendants = descendants

    def _get_diff(
        self,
        commodity: Commodity,
        snapshot: CommodityTreeSnapshot,
        relation: TreeNodeRelation,
    ) -> SnapshotDiff:
        """
        Returns a snapshot diff for a given relation on a sinlge commodity.

        For detailed overview on snapshot diffs, see the docs for the SnapshotDiff class.

        You can get one diff per commodity and relation type
        (e.g. diff the children of '9999.20.00.00' or diff the siblings of '9999.30.20.10')
        """
        if snapshot.moment.clock_type != self.moment.clock_type:
            raise ValueError("Cannot diff snapshots with different clock types.")

        attr = f"get_{relation.value}"

        if hasattr(self, attr) is False:
            raise ValueError("Unknown relation")

        values = [
            getattr(self, attr)(commodity),
            getattr(snapshot, attr)(commodity),
        ]

        return SnapshotDiff(
            commodity=commodity,
            relation=relation,
            values=values,
        )


@dataclass
class CommodityCollection(CommodityTreeBase):
    """
    Provides a model for a collection of related commodities.

    The collection may include all sorts of commodities,
    regardless of the validity or version of the related GoodsNomenclature object.

    This approach enables support for:
    1. Applying changes in-memory to the collections with create, update and delete actions
    2. Taking snapshots using either the calendar or transaction clocks.

    NOTE: This model does not keep information about relationships
    since the commodity collection allows for members
    with related GoodsNomenclature objects that are deprecated, current or future.

    To see the commodity tree hierarchy for a given moment, get a snapshot
    - see the docs to `CommodityCollection.get_snapshot` method for more details.
    """

    def update(self, changes: Sequence["CommodityChange"]) -> None:
        """
        Update the commodity collection using CommodityChange constructs.

        Change constructs are responsible for validating the sanity of pending changes.
        All this method needs to do is apply the correct business logic given the update type:
        - remove the current commodity for update_type delete
        - remove the current commodity and add the candidate commodity for update type update
        - add the candidate commodity for update type create

        For detials on change constructs and current vs candidate commodities in a change,
        see the docs for the CommodityChange model.
        """
        for change in changes:
            try:
                self.commodities.remove(change.current)
            except ValueError:
                pass

            if change.update_type == UpdateType.DELETE:
                continue

            self.commodities.append(change.candidate)

    def get_combined_clock_snapshot(
        self,
        transaction: Transaction,
        snapshot_date: date,
    ) -> CommodityTreeSnapshot:
        """
        Return a commodity tree snapshot as of a certain calendar date.

        If the optional snapshot_date argument is not provided, this method will
        return the snapshot as of today.
        """
        return self._get_snapshot(
            transaction=transaction,
            snapshot_date=snapshot_date,
        )

    def get_transaction_clock_snapshot(
        self,
        transaction: Transaction,
    ) -> CommodityTreeSnapshot:
        """
        Return a commodity tree snapshot as of a certain transaction (based on
        transaction id).

        If the optional transaction_id argument is not provided, this method
        will return the snapshot as of the most recent transaction in the db and
        will assign as the snapshot moment the highest transaction id across all
        snapshot commodities.
        """
        return self._get_snapshot(transaction=transaction)

    @property
    def current_snapshot(self) -> CommodityTreeSnapshot:
        """
        Returns a commodity tree "current" snapshot.

        A current snapshot only includes current record versions for commodities
        that are valid as of the current date.
        """
        return self._get_snapshot(transaction=self.max_transaction)

    def _get_snapshot(
        self,
        transaction: Transaction,
        snapshot_date: Optional[date] = None,
    ) -> CommodityTreeSnapshot:
        if transaction is None:
            raise ValueError(
                "SnapshotMoments require a transaction.",
            )

        if not snapshot_date:
            snapshot_date = date.today()

        moment = SnapshotMoment(
            transaction=transaction,
            date=snapshot_date,
        )

        commodities = self._get_snapshot_commodities(transaction, snapshot_date)

        return CommodityTreeSnapshot(
            moment=moment,
            commodities=commodities,
        )

    def _get_snapshot_commodities(
        self,
        transaction: Transaction,
        snapshot_date: date,
    ) -> List[Commodity]:
        """
        Returns the list of commodities than belong to a snapshot.

        This method needs to be very efficient -
        In particular, it should require the same number
        of database round trips regardless of the level
        of the root commodity in the tree.

        The solution is fetch all goods matching the snapshot moment
        (incl. potentially multiple versions of each)
        and then call a new util method get_latest_version,
        which efficiently yields only the latest version
        of each good from within the returned queryset.

        We then efficiently find the commodities in our collection
        that match the latest_version goods.
        """
        item_ids = {c.get_item_id() for c in self.commodities if c.obj}
        goods = GoodsNomenclature.objects.approved_up_to_transaction(
            transaction,
        ).filter(
            item_id__in=item_ids,
            valid_between__contains=snapshot_date,
        )

        latest_versions = get_latest_versions(goods)
        pks = {good.pk for good in latest_versions}

        keyed_collection = {c.obj.pk: c for c in self.commodities if c.obj}
        return [commodity for pk, commodity in keyed_collection.items() if pk in pks]

    def __copy__(self) -> "CommodityCollection":
        """Returns an independent copy of the collection."""
        return CommodityCollection(copy(self.commodities))


@dataclass
class SideEffect(BaseModel):
    """
    "Provides a model for commodity change side effects.

    A side effect is simply a pending action taken to preempt a business rule
    violation related to a commodity code change.

    The attributes of a side effect are as follows:
    - obj: the affected model (e.g. a Measure, a FootnoteAssociation, etc.)
    - update_type: the required update type to remedy the business rule violation
    - code: the changing commodity code that caused the side effect
    - rule: the business rule that was violated
    - variant: an optional note to distinguish business rule violation scenarios
      (e.g. a business rule such as ME32 can be violated for more than one reason)
    - attrs: optional update attributes when the side effect update_type is Update;
      this should be null when the update type is Delete
    """

    obj: TrackedModel
    update_type: UpdateType
    code: CommodityCode
    rule: BusinessRule
    variant: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None

    def to_transaction(self, workbasket: WorkBasket) -> TrackedModel:
        order = self._get_preemptive_transaction_order(workbasket)
        attrs = self.attrs or {}

        with workbasket.new_transaction(order=order) as transaction:
            return self.obj.new_version(
                workbasket, transaction, update_type=self.update_type, **attrs
            )

    def _get_preemptive_transaction_order(self, workbasket: WorkBasket) -> int:
        last_order = (
            workbasket.transactions.filter(
                order__lt=0,
            )
            .order_by(
                "order",
            )
            .values_list("order", flat=True)
        )

        if not last_order:
            return PREEMPTIVE_TRANSACTION_SEED

        return last_order + 1

    def explain(self) -> dict[str, Any]:
        """Returns a dict explaining the context of the side effect."""
        identifier = "|".join(map(str, self.obj.get_identifying_fields().values()))
        identifier = f"{type(self.obj).__qualname__} {identifier}"

        br_identifier = self.rule.__qualname__ if self.rule else "None"
        if self.variant:
            br_identifier += self.variant

        return dict(
            commodity_code=self.code.dot_code,
            business_rule=br_identifier,
            affected=identifier,
            affected_code=self.obj.goods_nomenclature.code.dot_code,
            update_type=self.update_type.name,
        )


@dataclass
class CommodityChange(BaseModel):
    """
    "Provides a model for commodity collection change requests.

    The model supports two Commodity instances:
    - current refers to an member of the commodity collection pre-change
    - candidate refers to a new commmodity (state) that represents the pending change

    The update type implies whether current and/or candidate are required
    (and the post-init validation will ensure this rule is enforced):
    - for create, only candidate is required
    - for delete, only current is required
    - for update, both current and candidate are required.

    NOTE: There is an option to ignore validation rules
    (in which case the validation method would log warn messages rather than raise errors);
    This is done in view of the fact that in the context of HS22 for example
    we will need to be in sync with the EU on any changes to the goods nomenclature,
    and deal with any repercussions of this downstream.
    """

    collection: CommodityCollection
    update_type: UpdateType
    current: Optional[Commodity] = None
    candidate: Optional[Commodity] = None
    ignore_validation_rules: bool = False

    def __post_init__(self) -> None:
        """Triggers validation on the fields of the model upon instantiation."""
        self.validate()
        self.preempt_side_effects()
        super().__post_init__()

    def validate(self) -> None:
        """
        Validates the sanity of the field values for the change model instance.

        There are two types of validation checks: a) ensure that the current and
        candidate fields are provided where required by the update type b)
        ensure that the requested changes makes sense in the context of the
        affected commodity collection c) ensure that the requested changes do
        not violate business rules
        """
        if self.candidate is not None:
            candidate = self.collection.get_commodity(
                self.candidate.get_item_id(),
                self.candidate.get_suffix(),
            )
        if self.current is not None:
            current = self.collection.get_commodity(
                self.current.get_item_id(),
                self.current.get_suffix(),
            )

        if self.update_type == UpdateType.CREATE:
            if self.candidate is None:
                self._handle_validation_issue("no commodity was provided")

            if candidate is not None:
                self._handle_validation_issue(
                    "the commodity already exists in the group",
                )

        else:
            if self.current is None:
                self._handle_validation_issue("a current commodity was not provided")

            if current != self.current:
                self._handle_validation_issue(
                    "there is no matching commodity in the commodity collection",
                )

        if self.update_type == UpdateType.UPDATE:
            if self.current == self.candidate:
                self._handle_validation_issue(
                    "the current and new versions are identical",
                    warn_only=True,
                )

            if candidate == self.candidate:
                self._handle_validation_issue(
                    "there is no effective change to the commodity",
                )

    def preempt_side_effects(self) -> None:
        """
        Preempt business rule violations due to the requested commodity change.

        See ADR13 for the scenarios covered for update or delete type changes.
        """
        self.side_effects = {}
        before, after = self._get_before_and_after_snapshots()

        if self.update_type == UpdateType.DELETE:
            self._handle_delete_side_effects(before)
        elif self.update_type == UpdateType.UPDATE:
            self._handle_update_side_effects(before, after)

        if self.update_type != UpdateType.CREATE:
            self._handle_hierarchy_side_effects(before, after)

    def _handle_delete_side_effects(self, before: CommodityTreeSnapshot) -> None:
        """
        Preempt business rule violations due to commodity code deletes.

        NOTE: Below are cases where underlying business rule logic
        could not be used for this use-case
        and where a corresponding refactor
        of the respective business rule or its parent class
        would be out-of-scope for this ticket:

        - NIG34: Checks whether the good is in "use" but does not provide related measures.
        - NIG35: Not used as it is redundant in this context after NIG34
        """
        # NIG34 / NIG35
        for measure in before.get_dependent_measures(self.current, self.as_at_date):
            self._add_pending_delete(measure, cbr.NIG34)

        # No BR: delete related footnote associations
        qs = FootnoteAssociationGoodsNomenclature.objects.latest_approved()
        for association in qs.filter(
            goods_nomenclature__item_id=self.current.get_item_id(),
        ):
            self._add_pending_delete(association, None)

    def _handle_update_side_effects(
        self,
        before: CommodityTreeSnapshot,
        after: CommodityTreeSnapshot,
    ) -> None:
        """
        Preempt business rule violations due to commodity code updates.

        NOTE:
        1. NIG35 is not used as it is redundant in this context after NIG34
        2. For some rules invoked from a measure's point of view (esp. ME7)
          there is no need to invoke them when we already know
          the changing commodity and whether it violates a condition;
          however, for consistency we still apply these rules.
        """

        good = self.candidate.good

        footnote_associations = (
            FootnoteAssociationGoodsNomenclature.objects.latest_approved().filter(
                goods_nomenclature__item_id=self.current.get_item_id(),
            )
        )
        measures = self._get_dependent_measures(before, after)

        # NIG30 / NIG31
        uncontained_measures = cbr.NIG30().uncontained_measures(good)

        if uncontained_measures.exists():
            for measure in uncontained_measures.order_by("sid"):
                self._handle_validity_conflicts(good, measure, cbr.NIG30)

        # NIG22: Invoked from the POV of a footnote association
        # here, find all related associations and invoke the BR
        # (inefficient for this workflow, but consistent use of BR-s)
        for association in footnote_associations:
            try:
                cbr.NIG22(good.transaction).validate(association)
            except BusinessRuleViolation:
                self._handle_validity_conflicts(good, association, cbr.NIG22)

        # ME7: Invoked from the POV of a measure
        # here, find all related measures and invoke the BR
        # (inefficient for this workflow, but consistent use of BR-s)
        if self.candidate.obj.suffix != SUFFIX_DECLARABLE:
            for measure in measures:
                try:
                    mbr.ME7().validate(measure)
                except BusinessRuleViolation:
                    self._add_pending_delete(measure, mbr.ME7)

        # ME88: Invoked from the POV of a measure
        # here, find all related measures and invoke the BR
        # (inefficient for this workflow, but consistent use of BR-s)
        if len(self.candidate.code.trimmed_code) > len(self.current.code.trimmed_code):
            obj = self.candidate.obj or good
            for measure in obj.measures.all():
                try:
                    mbr.ME88().validate(measure)
                except BusinessRuleViolation:
                    self._add_pending_delete(measure, mbr.ME88)

        # ME71 / NIG18: Invoked from the POV-s of footnote associations
        # here, find all related footnote associations
        # to the commodity as well its measures, and invoke the BR-s
        # (inefficient for this workflow, but consistent use of BR-s)
        if self.candidate.code.is_taric_subheading:
            for association in footnote_associations:
                try:
                    cbr.NIG18().validate(association)
                except BusinessRuleViolation:
                    self._add_pending_delete(association, cbr.NIG18)

            qs = FootnoteAssociationMeasure.objects.latest_approved()
            for measure in measures:
                for association in qs.filter(footnoted_measure=measure):
                    try:
                        mbr.ME71().validate(association)
                    except BusinessRuleViolation:
                        self._add_pending_delete(association, mbr.ME75)

    def _handle_validity_conflicts(
        self,
        good: GoodsNomenclature,
        obj: TrackedModel,
        rule: BusinessRule,
    ) -> None:
        """Handle conflicts related to validity span rule violations."""
        gvb = good.valid_between
        ovb = obj.valid_between

        # If obj validity does not overlap the good validity at all,
        # mark the object for deletion
        if date_ranges_overlap(gvb, ovb) is False:
            self._add_pending_delete(obj, rule)
            return

        # Determine whether the obj validity is trimmed
        # from start date, end date, or both
        valid_between = contained_date_range(ovb, gvb)

        if valid_between == ovb:
            return

        attrs = dict(
            valid_between=valid_between,
        )

        if type(obj) == Measure:
            attrs["terminating_regulation"] = obj.generating_regulation

        self._add_pending_update(obj, attrs, rule)

    def _handle_hierarchy_side_effects(
        self,
        before: CommodityTreeSnapshot,
        after: CommodityTreeSnapshot,
    ) -> None:
        """
        Preempt business rule violations related to changes in hierarchy.

        NOTE: There are several reasons why we can't use ME32 directly here,
        even if we are willing to sacrifice performance:
        - ME32 has no ability to preview the "after" snapshot;
          this is the only business rule where this is a fatal problem
          as here we need to assess business rule violations
          in the context of related nodes in a changing hierarchy
        - ME32 relies on GoodsNomenclatureIndentNodes and paths
          as the means of identifying ancestors and descendants

        Importantly, the actual ME32 is still going to be run downstream
          when we validate a workbasket with transactions reflecting:
          a) commodity changes (e.g. captured from the selective xml importer)
          b) the side effects of these changes in terms of
          updates/deletions of related measures or footnote associations.

        TODO: Refactor ME32 to consolidate the two use-case scenarios.
        """

        def _get_measure_key(m: Measure) -> Tuple[str, str, str, str, int]:
            """
            Returns a fingerprint for a measure based on select field values.

            Any other measure with the same fingerprint can trigger a violation
            of ME32 with respect to this measure if the validity spans of the
            two measures overlap as well.
            """
            try:
                order_number = (m.order_number or m.dead_order_number).order_number
            except AttributeError:
                order_number = ""

            try:
                additional_code = (m.additional_code or m.dead_additional_code).code
            except AttributeError:
                additional_code = ""

            return (
                m.measure_type.sid,
                m.geographical_area.area_id,
                order_number,
                additional_code,
                m.reduction,
            )

        # Check if the changing commodity has ME32 clashes in its new hierarchy
        if self.update_type == UpdateType.UPDATE:
            self.candidate.get_valid_between().upper

            measures = {
                _get_measure_key(measure): measure
                for measure in after.get_dependent_measures(
                    self.candidate,
                    self.as_at_date,
                )
            }

            for attr in ["get_ancestors", "get_descendants"]:
                for relative in getattr(after, attr)(self.candidate):
                    related_measures = after.get_dependent_measures(
                        relative,
                        self.as_at_date,
                    )

                    for related_measure in related_measures:
                        key = _get_measure_key(related_measure)

                        try:
                            measure = measures[key]

                            if date_ranges_overlap(
                                measure.valid_between,
                                related_measure.valid_between,
                            ):
                                self._add_pending_delete(related_measure, mbr.ME32, "a")
                        except KeyError:
                            continue

        measures = {
            _get_measure_key(measure): measure
            for measure in before.get_dependent_measures(self.current, self.as_at_date)
        }

        # Check if commodity's before-children have new parents
        for child in before.get_children(self.current):
            # If the commodity's before-child has a new parent...
            if before.compare_parents(child, after).diff:
                # ...then check if before-child has ME32 clashes with any new ancestors
                for ancestor in after.get_ancestors(child):
                    ancestor_measures = after.get_dependent_measures(
                        ancestor,
                        self.as_at_date,
                    )

                    for ancestor_measure in ancestor_measures:
                        key = _get_measure_key(ancestor_measure)

                        try:
                            measure = measures[key]
                            if date_ranges_overlap(
                                measure.valid_between,
                                ancestor_measure.valid_between,
                            ):
                                self._add_pending_delete(
                                    ancestor_measure,
                                    mbr.ME32,
                                    "b",
                                )
                        except KeyError:
                            continue

    def _add_pending_delete(
        self,
        obj: TrackedModel,
        rule: BusinessRule,
        variant: Optional[str] = None,
    ) -> None:
        """Add a pending related object delete operation to side effects."""
        key = get_model_identifier(obj)

        self.side_effects[key] = SideEffect(
            obj=obj,
            update_type=UpdateType.DELETE,
            code=(self.current or self.candidate).code,
            rule=rule,
            variant=variant,
        )

    def _add_pending_update(
        self,
        obj: TrackedModel,
        attrs: Dict[str, Any],
        rule: BusinessRule,
        variant: Optional[str] = None,
    ) -> None:
        """Add a pending related object update operation to side effects."""
        key = get_model_identifier(obj)

        try:
            self.side_effects[key].attrs.update(attrs)
        except KeyError:
            self.side_effects[key] = SideEffect(
                obj=obj,
                update_type=UpdateType.UPDATE,
                code=(self.candidate or self.current).code,
                rule=rule,
                variant=variant,
                attrs=attrs,
            )

    def _handle_validation_issue(self, msg: str, warn_only: bool = False) -> None:
        """Logs a warning message or raises an error."""

        if self.ignore_validation_rules or warn_only:
            logger.warning(f"The operation is {self.update_type} but {msg}")
        else:
            raise CommodityChangeException(msg, self)

    def _get_before_and_after_snapshots(
        self,
    ) -> Tuple[CommodityTreeSnapshot, CommodityTreeSnapshot]:
        clone = copy(self.collection)

        commodity = self.current or self.candidate

        if commodity.good:
            before = clone.get_transaction_clock_snapshot(commodity.good.transaction)
        else:
            before = clone.current_snapshot

        clone.update([self])

        commodity = self.candidate or self.current
        after = clone.get_transaction_clock_snapshot(commodity.good.transaction)

        return before, after

    def _get_dependent_measures(
        self,
        before: CommodityTreeSnapshot,
        after: CommodityTreeSnapshot,
    ) -> Set[Measure]:
        b = before.get_dependent_measures(
            self.current or self.candidate,
            self.as_at_date,
        )
        a = after.get_dependent_measures(
            self.candidate or self.current,
            self.as_at_date,
        )
        return set(a).union(set(b))

    @property
    def as_at_date(self) -> date:
        """
        Returns the treshold date for the commodity code change.

        Dependent measures (or other dependent models with validity spans)
        would be exclude those with effective end date before this date.

        In the case of a commodity UPDATE or DELETE,
        the treshold the commodity's validity end date.
        In the case of a commodity CREATE,
        the treshold is the commodity's validity start date.
        """
        if self.candidate:
            if self.update_type == UpdateType.UPDATE:
                return self.candidate.get_valid_between().upper
            else:
                return self.candidate.get_valid_between().lower
        return self.current.get_valid_between().upper


# TODO: Move the loader to a more appropriate module
class CommodityCollectionLoader:
    """Provides a loader of collections of commodities from the tariff db."""

    def __init__(self, prefix: str) -> None:
        """
        Instantiate the loader.

        The prefix can be any string with length of 2 characters or more.
        The loader will select any commodity with a code that begins with the prefix.
        For example:
        - if the prefix is '02', all commodities under HS chapter 2 will be loaded
        - if the prefix is '020202', all commodities under the respective subheading will be loaded
        - a prefix such as '0202021' is allowed also, assuming this makes sense for a given use-case.

        NOTE: The commodities are NOT actually loaded at this stage.
        Check the `load` method of this class for details.
        """
        if len(prefix) < 2:
            raise ValueError(
                "The minimum prefix length is 2 characters, which denotes an HS chapter.",
            )

        self.prefix = prefix

    def load(
        self,
        current_only: bool = False,
        effective_only: bool = False,
    ) -> CommodityCollection:
        """
        Returns a CommodityCollection including all commodities that match the
        prefix.

        NOTE: If the current_only flag is set to True, the loader will only add commodities
        that are based on current versions of GoodsNomenclature objects,
        and will only select objects with with a validity range that includes today.
        This is equivalent to getting the current snapshot of the commodity collection
        (see the docs for CommodityCollection for more detail on snapshots.)
        """
        qs = GoodsNomenclature.objects

        if current_only:
            qs = qs.latest_approved()

        if effective_only:
            qs = qs.filter(
                valid_between__contains=date.today(),
            )

        qs = qs.filter(item_id__startswith=self.prefix)

        commodities = [Commodity(obj=obj) for obj in qs.all()]

        return CommodityCollection(commodities=commodities)


class CommodityChangeException(ValueError):
    def __init__(self, msg: str, change: CommodityChange) -> None:
        super().__init__(f"Commodity {change.update_type} error: {msg}")


class CommodityTreeSnapshotException(ValueError):
    pass


def get_model_preferred_key(obj: TrackedModel) -> str:
    """
    Returns the preferred identifier key name for the model, if defined. Many
    models in the Taric specification have a field that contains the identifier
    or descriptor for each object. Examples include:

    - item_id for GoodsNomenclature
    - area_id for GeographicalArea
    - sid for Measure (among others)
    - order_number for QuotaOrderNumber
    - code for MeasurementUnit (among others)
    This method will return the preferred key name
    where it has been specified, otherwise the primary key name.
    """
    key = TRACKEDMODEL_IDENTIFIER_KEYS.get(obj._meta.label)

    if key is None:
        model_field_names = [field.name for field in obj._meta.fields]

        if TRACKEDMODEL_IDENTIFIER_FALLBACK_KEY in model_field_names:
            key = TRACKEDMODEL_IDENTIFIER_FALLBACK_KEY
        else:
            key = TRACKEDMODEL_PRIMARY_KEY

    return key


def get_model_identifier(obj: TrackedModel) -> str:
    """Returns the preferred identifier for a model."""
    identifier = obj.identifying_fields_to_string
    label = obj._meta.label
    return f"{label}: {identifier}"


# TODO: Potentially move to a more prominent place in the django project
class TrackedModelReflection:
    """
    A generic class for tracked model reflections.

    For details, see get_tracked_model_reflection below.
    """

    def __init__(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)


def get_tracked_model_reflection(
    obj: TrackedModel, transaction: Transaction = None, **overrides
):
    """
    Returns a reflection of a TrackedModel object.

    A reflection is different from `TrackedModel.copy`:
    - it attaches references to the same related models as the underlying object
      (rather than create new versions of them)
    - it is not meant to be written to db

    The benefit of using a reflection is that scenarios such as
    handling of commodity changes can produce side effects
    referring to the actual related models of the underlying object
    rather than new versions of them linked to a copy of the object.
    """
    fields = (field for field in obj._meta.get_fields())
    attrs = {}

    for field in fields:
        try:
            attrs[field.name] = getattr(obj, field.name)
        except AttributeError:
            continue
        except field.related_model.DoesNotExist:
            attrs[field.name] = None

    attrs.update(
        {attr: value for attr, value in overrides.items() if hasattr(obj, attr)},
    )

    if transaction:
        attrs["transaction"] = transaction

    return TrackedModelReflection(**attrs)


@dataclass
class CommodityChapterChanges:
    collection: CommodityCollection
    changes: list[CommodityChange] = field(default_factory=list)


class CommodityChangeRecordLoader:
    """Provides a loader for commodity changes based on imported taric
    records."""

    def __init__(self) -> None:
        """Instantiates the loader."""
        self.chapter_changes: dict[str, CommodityChapterChanges] = {}

    def load(self, transaction: Transaction) -> list[CommodityChange]:
        """
        Converts transaction records to corresponding CommodityChange objects.

        Records in the transaction are grouped
        based on the changing commodity they relate to.
        In any given transaction, there will be 400-type records
        relating to one or more changing commodities.
        Here the 400-type records are grouped based on
        the changing commodity they relate to,
        and each group will produce one pending commodity change.

        Note: Since side effects of pending commodity changes
        (with related remedies) are identified post instantiation,
        this means that once commodity change records are loaded here,
        all remedies are available to be appended
        as transactions to the import workbasket -
        CommodityChange provides the functionality
        to represent a remedy as a transaction as well.
        """
        record_group = TARIC_RECORD_GROUPS["commodities"]

        matching_records = [
            (self._get_record_commodity_code(obj), obj)
            for obj in transaction.tracked_models.all()
            if obj.record_identifier in record_group
        ]

        sorted_records = sorted(matching_records, key=lambda x: x[0])
        grouped_records = groupby(sorted_records, key=lambda x: x[0])

        for commodity_code, records in grouped_records:
            self.add_pending_change(commodity_code, records)

    def add_pending_change(
        self,
        commodity_code: str,
        records: tuple[str, dict[str, TrackedModel]],
    ) -> None:
        """
        Produces a commodity change instance based on a group of 400-type
        records that relate to the same changing commodity.

        Note: Ultimately only changes that affect the hierarchy
        (item_id, suffix, validity period, and indent)
        need to result in a CommodityChange record.

        These changes will be found either in the
        40000 or 40005 record in the group
        (GoodsNomenclature and GoodsNomenclatureIndent).

        Changes to descriptions, description periods,
        origins or successors are not relevant here
        (any changes to origin or successor related commodities
        will have been handled on their own separately).
        """
        chapter = commodity_code[:4]
        chapter_changes = self._get_or_create_chapter_changes(chapter)

        records_by_identifier = {obj.record_identifier: obj for _, obj in records}

        good = records_by_identifier.get("40000")
        indent = records_by_identifier.get("40005")

        if not (good or indent):
            return

        if not good:
            good = indent.indented_goods_nomenclature

        indent_ = indent.indent if indent else None
        current = self._get_current_commodity(good, indent_)

        candidate = self._create_candidate_commodity(good)

        change = CommodityChange(
            collection=chapter_changes.collection,
            update_type=good.update_type,
            current=current,
            candidate=candidate,
            ignore_validation_rules=True,
        )

        chapter_changes.changes.append(change)

    def _get_or_create_chapter_changes(self, chapter: str) -> CommodityChapterChanges:
        """Returns an instance of CommodityCollectionLoader for the chapter."""
        if chapter not in self.chapter_changes:
            loader = CommodityCollectionLoader(prefix=chapter)
            collection = loader.load()

            self.chapter_changes[chapter] = CommodityChapterChanges(
                collection=collection,
            )

        return self.chapter_changes[chapter]

    def _get_indent(self, indent_record: dict[str, Any]) -> Optional[int]:
        """Returns the indent level from an indent record (40005), if such
        record exists in the record group for a changing commodity."""
        if indent_record:
            return indent_record["goods_nomenclature_indent"]["indent"]

    def _get_update_type(self, commodity_record: dict[str, Any]) -> UpdateType:
        """Returns the update type for the commodity record."""
        if commodity_record:
            update_flag = int(commodity_record["update_type"])
            return UpdateType(update_flag)

        return UpdateType.UPDATE

    def _get_current_commodity(
        self,
        good: GoodsNomenclature,
        indent: Optional[int] = None,
    ) -> Optional[Commodity]:
        """Returns a commodity wrapper for the current good object as of the
        record transaction."""
        if good.update_type == UpdateType.CREATE:
            return None

        return Commodity(
            obj=good,
            indent=indent,
        )

    def _create_candidate_commodity(
        self,
        good: GoodsNomenclature,
    ) -> Optional[Commodity]:
        """Returns a candidate commodity wrapper with the commodity record's
        attributes."""
        if good.update_type == UpdateType.DELETE:
            return None

        return Commodity(obj=good)

    def _get_taric_date_range(self, data: dict[str, Any]) -> TaricDateRange:
        """Returns a TaricDateRange instance for the record's validity
        period."""
        valid_between = copy(data["valid_between"])

        if "upper" not in valid_between:
            valid_between["upper"] = None

        start_date, end_date = map(
            lambda x: date(*map(int, x.split("-"))) if x else None,
            valid_between.values(),
        )

        return TaricDateRange(start_date, end_date)

    def _get_record_commodity_code(self, obj: TrackedModel) -> str:
        """Returns the commodity code embedded in a taric record."""
        _, attr_name = COMMODITY_RECORD_ATTRIBUTES[obj.record_identifier]

        attrs = attr_name.split("__")
        result = obj
        for attr in attrs:
            result = getattr(result, attr)

        return result
