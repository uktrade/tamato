"""Includes dataclasses used in goods nomenclature hierarchy tree management."""
from __future__ import annotations

import logging
from copy import copy
from dataclasses import dataclass
from datetime import date
from hashlib import md5
from typing import Any
from typing import Optional
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
from common.business_rules import BusinessRuleViolation
from common.models.constants import ClockType
from common.models.dc.base import BaseModel
from common.models.records import TrackedModel
from common.models.transactions import Transaction
from common.util import TaricDateRange
from common.validators import UpdateType
from measures import business_rules as mbr
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure

logger = logging.getLogger(__name__)

__all__ = [
    "Commodity",
    "CommodityChange",
    "CommodityCollection",
    "CommodityCollectionLoader",
    "CommodityTreeSnapshot",
]

TTrackedModelIdentifier = Union[str, int]

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
    def code(self) -> str:
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
    def version(self) -> int:
        """
        Returns the version of the object.

        TrackedModel objects support version control. The version_group field
        holds pointers to all prior and current versions of a Taric record. The
        versions are ordered based on transaction id. This method returns the
        version number of the object based on the place of its transaction id in
        the version transaction ids sequence.
        """
        ids = self._get_transaction_ids()
        version = ids.index(self.obj.transaction.id) + 1
        return version

    @property
    def current_version(self) -> int:
        """Returns the current version of the Taric record."""
        return self.obj.version_group.versions.count()

    @property
    def is_current_version(self) -> bool:
        """Returns True if this is the current version of the Taric record."""
        return self.obj == self.obj.current_version

    def is_current_as_of_transaction(self, transaction: Transaction) -> bool:
        """Returns True if this is the current version of the record as of a
        given transaction."""
        return self.is_current_as_of_transaction_id(transaction.id)

    def get_current_version_as_of_transaction_id(
        self,
        transaction_id: Optional[int] = None,
    ) -> int:
        """Returns the current version of the record as of a given transaction
        id."""
        if transaction_id is None:
            return self.current_version

        ids = self._get_transaction_ids()
        return len([tid for tid in ids if tid <= transaction_id])

    def is_current_as_of_transaction_id(
        self,
        transaction_id: Optional[int] = None,
    ) -> bool:
        """Returns True if this is the current version of the record as of a
        given transaction id."""
        if transaction_id is None:
            return self.is_current_version

        current_version = self.get_current_version_as_of_transaction_id(transaction_id)
        return self.version == current_version

    def _get_transaction_ids(self) -> tuple[int]:
        """Returns the id-s of all transactions in the version group of the
        record."""
        transaction_ids = self.obj.version_group.versions.values_list(
            "transaction_id",
            flat=True,
        )
        return tuple(transaction_ids)

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
            and self.obj.valid_between == commodity.obj.valid_between
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

    commodities: list[Commodity]

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
    values: list[Union[Commodity, list[Commodity]]]

    @property
    def diff(self) -> list[Commodity]:
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
    either the calendar or transaction clock, but not both.
    Accordingly the moment field of this dataclass can be one of:
    - a calendar date (when the clock type is calendar)
    - a transaction id (when the clock type is transaction)

    For additional context on commodity trees, see the docs for CommodityTree.
    """

    commodities: list[Commodity]
    clock_type: ClockType
    moment: Union[date, int]
    edges: Optional[dict[str, Commodity]] = None

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
        - this is the responsiblity of the _sort method of this class
        2. Traversal of the sorted commodity collection is trivial:
        - the method keeps a running tally of the latest sorted commodity for a given indent
        - the parent of a commodity is the current object at (indent - 1)
        - the behaviour differs for 0-indent commodities:
          -- the method keeps a list of the prior sorted commodities
          -- this allows it to assign the correct parents for 0-indent headings.
        """
        chapters = {c.code.chapter for c in self.commodities}

        if len(chapters) != 1:
            msg = "All commodities in a group must be from the same HS chapter."
            raise CommodityTreeSnapshotException(msg)

        try:
            assert len(chapters) == 1
        except AssertionError:
            print("All commodities in a group must be from the same HS chapter.")
            raise

        self._sort()
        self._traverse()

        super().__post_init__()

    def get_parent(self, commodity: Commodity) -> Optional[Commodity]:
        """Returns the parent of a commodity in the snapshot tree."""
        try:
            return self.edges[commodity.identifier]
        except KeyError:
            return

    def get_siblings(self, commodity: Commodity) -> list[Commodity]:
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

    def get_children(self, commodity: Commodity) -> list[Commodity]:
        """Returns the children of a commodity in the snapshot tree."""
        return [c for c in self.commodities if self.get_parent(c) == commodity]

    def get_ancestors(self, commodity: Commodity) -> list[Commodity]:
        """Returns all ancestors of a commodity in the snapshot tree."""
        ancestors = []

        current = commodity

        while True:
            parent = self.get_parent(current)
            if parent is None:
                break
            ancestors.append(parent)
            current = parent

        return ancestors[::-1]

    def get_descendants(self, commodity: Commodity) -> list[Commodity]:
        """Returns all descendants of a commodity in the snapshot tree."""
        descendants = []

        generation = [commodity]

        while True:
            children = [
                child
                for commodity in generation
                for child in self.get_children(commodity)
            ]

            if len(children) == 0:
                break

            descendants.extend(children)
            generation = children

        return descendants

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

    @property
    def snapshot_date(self) -> Optional[date]:
        """Returns the snapshot date if it uses the calendar clock."""
        if self.clock_type == ClockType.CALENDAR:
            return self.moment

    @property
    def snapshot_transaction_id(self) -> Optional[int]:
        """Retruns the snapshot transaction if uses the transaction clock."""
        if self.clock_type == ClockType.TRANSACTION:
            return self.moment

    @property
    def hash(self) -> str:
        """Returns a hash based on the sorted identifiers of snapshot
        commodities."""
        md5_hash = md5()
        value = ".".join(sorted(c.identifier for c in self.commodities))
        md5_hash.update(value.encode())
        return md5_hash.hexdigest()

    @property
    def identifier(self) -> str:
        """Returns a unique identifier for the snapshot."""
        prefix = "tx_" if self.clock_type == ClockType.TRANSACTION else ""
        return f"{prefix}{self.moment}.{self.hash}"

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
        indents = {0: []}
        edges = {}

        for commodity in self.commodities:
            indent = commodity.get_indent()

            if indent == 0:
                try:
                    parent = indents[indent][-1]
                except IndexError:
                    parent = None
            elif indent == 1:
                try:
                    parent = indents[indent - 1][-1]
                except IndexError:
                    parent = None
            else:
                try:
                    parent = indents[indent - 1]
                except KeyError:
                    parent = None

            edges[commodity.identifier] = parent

            if indent == 0:
                indents[indent].append(commodity)
            else:
                indents[indent] = commodity

        self.edges = edges

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
        if snapshot.clock_type != self.clock_type:
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

    def __eq__(self, snapshot: CommodityTreeSnapshot) -> bool:
        """Returns True for snapshots with the same clock types and commoditie
        collections."""
        return self.identifier == snapshot.identifier


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
    - see the docs to get_snapshot method of this class for more details.
    """

    def update(self, changes: tuple["CommodityChange"]) -> None:
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

    def get_calendar_clock_snapshot(
        self,
        snapshot_date: Optional[date] = None,
    ) -> CommodityTreeSnapshot:
        """
        Return a commodity tree snapshot as of a certain calendar date.

        If the optional snapshot_date argument is not provided, this method will
        return the snapshot as of today.
        """
        snapshot_date = snapshot_date or date.today()

        commodities = [
            commodity
            for commodity in self.commodities
            if commodity.end_date is None or commodity.end_date >= snapshot_date
            if commodity.start_date <= snapshot_date
        ]

        return CommodityTreeSnapshot(
            commodities=commodities,
            clock_type=ClockType.CALENDAR,
            moment=snapshot_date,
        )

    def get_transaction_clock_snapshot(
        self,
        transaction_id: Optional[int] = None,
    ) -> CommodityTreeSnapshot:
        """
        Return a commodity tree snapshot as of a certain transaction (based on
        transaction id).

        If the optional transaction_id argument is not provided, this method
        will return the snapshot as of the most recent transaction in the db and
        will assign as the snapshot moment the highest transaction id across all
        snapshot commodities.
        """
        today = date.today()

        commodities = [
            commodity
            for commodity in self.commodities
            if commodity.end_date is None or commodity.end_date >= today
            if commodity.start_date <= today
            if commodity.is_current_as_of_transaction_id(transaction_id)
        ]

        if transaction_id is None:
            transaction_id = max(
                [
                    transaction_id
                    for commodity in self.commodities
                    for transaction_id in commodity._get_transaction_ids()
                ],
            )

        return CommodityTreeSnapshot(
            commodities=commodities,
            clock_type=ClockType.TRANSACTION,
            moment=transaction_id,
        )

    @property
    def current_snapshot(self) -> CommodityTreeSnapshot:
        """
        Returns a commodity tree "current" snapshot.

        A current snapshot only includes current record versions for commodities
        that are valid as of the current date.
        """

        today = date.today()

        commodities = [
            commodity
            for commodity in self.commodities
            if commodity.end_date is None or commodity.end_date >= today
            if commodity.start_date <= today
            if commodity.is_current_version
        ]

        return CommodityTreeSnapshot(
            commodities=commodities,
            clock_type=ClockType.CALENDAR,
            moment=today,
        )

    def __copy__(self) -> "CommodityCollection":
        """Returns an independent copy of the collection."""
        return CommodityCollection(copy(self.commodities))


@dataclass
class SideEffect(BaseModel):
    """
    "Provides a model for commodity change side effects.

    A side effect is simply a pending action taken to preempt a business rule
    violation related to a commodity code change.
    """

    obj: TrackedModel
    update_type: UpdateType
    attrs: dict[str, Any] = None


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
    side_effects: Optional[dict[TTrackedModelIdentifier, SideEffect]] = None

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
                self.candidate.code,
                self.candidate.suffix,
            )
        if self.current is not None:
            current = self.collection.get_commodity(
                self.current.code,
                self.current.suffix,
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

        if self.update_type == UpdateType.DELETE:
            self._handle_delete_side_effects()
        elif self.update_type == UpdateType.UPDATE:
            self._handle_update_side_effects()

        if self.update_type != UpdateType.CREATE:
            self._handle_hierarchy_side_effects()

    def _handle_delete_side_effects(self) -> None:
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
        good = self.current.obj

        # NIG34 / NIG35
        for measure in good.dependent_measures:
            self._add_pending_delete(measure)

        # No BR: delete related footnote associations
        qs = FootnoteAssociationGoodsNomenclature.objects.latest_approved()
        for association in qs.filter(
            goods_nomenclature__item_id=self.current.code,
        ):
            self._add_pending_delete(association)

    def _handle_update_side_effects(self) -> None:
        """
        Preempt business rule violations due to commodity code updates.

        NOTE:
        1. NIG35 is not used as it is redundant in this context after NIG34
        2. For some rules invoked from a measure's point of view (esp. ME7)
          there is no need to invoke them when we already know
          the changing commodity and whether it violates a condition;
          however, for consistency we still apply these rules.
        """

        good = self.candidate.obj

        footnote_associations = good.footnote_associations.all()
        measures = good.dependent_measures

        # NIG30 / NIG31
        try:
            cbr.NIG30().validate(good)
        except BusinessRuleViolation:
            for measure in measures:
                self._handle_validity_conflicts(measure)

        # NIG22: Invoked from the POV of a footnote association
        # here, find all related associations and invoke the BR
        # (inefficient for this workflow, but consistent use of BR-s)
        for association in footnote_associations:
            try:
                cbr.NIG22().validate(association)
            except BusinessRuleViolation:
                self._handle_validity_conflicts(association)

        # ME7: Invoked from the POV of a measure
        # here, find all related measures and invoke the BR
        # (inefficient for this workflow, but consistent use of BR-s)
        if self.candidate.obj.suffix != SUFFIX_DECLARABLE:
            for measure in measures:
                try:
                    mbr.ME7().validate(measure)
                except BusinessRuleViolation:
                    self._add_pending_delete(measure)

        # ME88: Invoked from the POV of a measure
        # here, find all related measures and invoke the BR
        # (inefficient for this workflow, but consistent use of BR-s)
        if len(self.candidate.code.trimmed_code) > len(self.current.code.trimmed_code):
            for measure in good.measures.all():
                try:
                    mbr.ME88().validate(measure)
                except BusinessRuleViolation:
                    self._add_pending_delete(measure)

        # ME71 / NIG18: Invoked from the POV-s of footnote associations
        # here, find all related footnote associations
        # to the commodity as well its measures, and invoke the BR-s
        # (inefficient for this workflow, but consistent use of BR-s)
        if self.candidate.code.is_taric_subheading:
            for association in footnote_associations:
                try:
                    cbr.NIG18().validate(measure)
                except BusinessRuleViolation:
                    self._add_pending_delete(association)

            qs = FootnoteAssociationMeasure.objects.latest_approved()
            for measure in measures:
                for association in qs.filter(footnoted_measure=measure):
                    try:
                        mbr.ME71().validate(association)
                    except BusinessRuleViolation:
                        self._add_pending_delete(association)

    def _handle_validity_conflicts(self, obj: TrackedModel) -> None:
        """Handle conflicts related to validity span rule violations."""
        good = self.candidate.obj

        gvb = good.valid_between
        ovb = obj.valid_between

        # If obj validity does not overlap the good validity at all,
        # mark the object for deletion
        if (ovb.upper and gvb.lower > ovb.upper) or (
            gvb.upper and gvb.upper < ovb.lower
        ):
            self._add_pending_delete(obj)
            return

        # Determine whether the obj validity is trimmed
        # from start date, end date, or both
        start_date = None
        end_date = None

        if gvb.upper and ovb.upper and gvb.upper < ovb.upper:
            end_date = gvb.lower
        if gvb.lower > ovb.lower:
            start_date = gvb.upper

        # Circuit breaker for cases where the obj is spanned by the good
        if start_date is None and end_date is None:
            return

        # Mark the object for update with trimmed validity
        valid_between = TaricDateRange(
            start_date or ovb.lower,
            end_date or ovb.upper,
        )

        attrs = dict(
            valid_between=valid_between,
        )

        self._add_pending_update(obj, attrs)

    def _handle_hierarchy_side_effects(self) -> None:
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

        def _get_measure_key(m: Measure) -> str:
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

        def _validities_overlap(m1: Measure, m2: Measure) -> bool:
            """
            Returns True if two measures have overlapping validity spans.

            Algorithm:
            1. Sort the two measures on start_date
            2a. If the earlier measure has no end date, there is an overlap
            2b. If the earlier measure's end date is on or after,
                the later measure start date, there is an overlap

            NOTE: If the two measures also have the same "fingerprint"
            (see _get_measure_key() above), this will violate ME32.
            """
            earlier, later = sorted((m1, m2), key=lambda x: x.valid_between.lower)

            return (
                earlier.valid_between.upper is None
                or earlier.valid_between.upper >= later.valid_between.lower
            )

        commodity = self.candidate or self.current
        good = commodity.obj
        measures = {_get_measure_key(m): m for m in good.dependent_measures}

        clone = copy(self.collection)
        before = clone.current_snapshot
        clone.update([self])
        after = clone.current_snapshot

        # Check if the changing commodity has ME32 clashes in its new hierarchy
        for attr in ["get_ancestors", "get_descendants"]:
            for relative in getattr(after, attr)(commodity):
                related_measures = relative.obj.dependent_measures

                for related_measure in related_measures:
                    key = _get_measure_key(related_measure)

                    try:
                        measure = measures[key]

                        if _validities_overlap(measure, related_measure):
                            self._add_pending_delete(related_measure)
                    except KeyError:
                        continue

        # Check if commodity's before-children have new parents
        for child in before.get_children(self.current):
            # If the commodity's before-child has new parent...
            if before.compare_parents(child, after).diff:
                # ...then check if before-child has ME32 clashes with new ancestors
                for ancestor in after.get_ancestors(child):
                    ancestor_measures = ancestor.obj.dependent_measures

                    for ancestor_measure in ancestor_measures:
                        key = _get_measure_key(ancestor_measure)

                        try:
                            measure = measures[key]
                            if _validities_overlap(measure, ancestor_measure):
                                self._add_pending_delete(ancestor_measure)
                        except KeyError:
                            continue

    def _add_pending_delete(self, obj: TrackedModel) -> None:
        """Add a pending related object delete operation to side effects."""
        key = get_model_identifier(obj)

        self.side_effects[key] = SideEffect(
            obj=obj,
            update_type=UpdateType.DELETE,
        )

    def _add_pending_update(self, obj: TrackedModel, attrs: dict[str, Any]) -> None:
        """Add a pending related object update operation to side effects."""
        key = get_model_identifier(obj)

        try:
            self.side_effects[key].attrs.update(attrs)
        except KeyError:
            self.side_effects[key] = SideEffect(
                obj=obj,
                update_type=UpdateType.UPDATE,
                attrs=attrs,
            )

    def _handle_validation_issue(self, msg: str, warn_only: bool = False) -> None:
        """Logs a warning message or raises an error."""

        if self.ignore_validation_rules or warn_only:
            msg = f"The operation is {self.update_type} but {msg}"
            logger.warn(msg)
        else:
            raise CommodityChangeException(msg, self)


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

    def load(self, current_only: bool = False) -> CommodityCollection:
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
            qs = qs.latest_approved().filter(
                Q(valid_between__endswith=None)
                | Q(valid_between__endswith__gt=date.today()),
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
    """Returns the preferred identifierfor a model."""
    attr = get_model_preferred_key(obj)
    return getattr(obj, attr)
