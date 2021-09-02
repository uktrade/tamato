"""Includes dataclasses used in goods nomenclature hierarchy tree management."""
import logging
from dataclasses import dataclass
from datetime import date
from hashlib import md5
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from django.db.models import Q

from commodities import business_rules as cbr
from common.business_rules import BusinessRuleViolation
from common.models.meta.base import BaseModel
from common.models.meta.wrappers import TrackedModelWrapper
from common.models.records import TrackedModel
from common.util import TaricDateRange
from common.validators import UpdateType
from measures import business_rules as mbr
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure

from .orm import FootnoteAssociationGoodsNomenclature
from .orm import GoodsNomenclature
from .static import SUFFIX_DECLARABLE
from .static import ClockType
from .static import TreeNodeRelation

logger = logging.getLogger(__name__)

__all__ = [
    "Commodity",
    "CommodityChange",
    "CommodityCollection",
    "CommodityCollectionLoader",
    "CommodityTreeSnapshot",
]


@dataclass
class Commodity(TrackedModelWrapper):
    """
    Provides a wrapper of the GoodsNomenclature model.

    See the docs for TrackedModelWrapper for additional context.
    """

    obj: GoodsNomenclature
    indent: int = None

    @property
    def code(self) -> str:
        """Returns the commodity code."""
        return self.obj.item_id

    @property
    def chapter(self) -> str:
        """Returns the HS chapter for the commodity code."""
        return self.code[:2]

    @property
    def heading(self) -> str:
        """Returns the HS heading for the commodity code."""
        return self.code[:4]

    @property
    def subheading(self) -> str:
        """Returns the HS subheading for the commodity code."""
        return self.code[:6]

    @property
    def cn_subheading(self) -> str:
        """Returns the CN subheading for the commodity code."""
        return self.code[:8]

    @property
    def dot_code(self) -> str:
        """Returns the commodity code in dot format."""
        code = self.code
        return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"

    @property
    def trimmed_dot_code(self) -> str:
        """Returns the commodity code in dot format, without trailing zero
        pairs."""
        parts = self.dot_code.split(".")

        for i, part in enumerate(parts[::-1]):
            if part != "00":
                return ".".join(parts[: len(parts) - i])

    @property
    def trimmed_code(self) -> str:
        """Returns the commodity code without trailing zero pairs."""
        return self.trimmed_dot_code.replace(".", "")

    @property
    def suffix(self) -> str:
        """Returns the suffix of the commodity."""
        return self.obj.suffix

    @property
    def description(self) -> str:
        """Returns the description of the commodity."""
        obj = self.obj.descriptions.order_by("validity_start").last()
        return obj.description

    @property
    def start_date(self) -> date:
        """Returns the validity start date of the commodity."""
        return self.obj.valid_between.lower

    @property
    def end_date(self) -> Optional[date]:
        """Returns the validity end date of the commodity."""
        return self.obj.valid_between.upper

    @property
    def is_chapter(self) -> bool:
        """Returns true if the commodity code represents a HS chapter."""
        return self.trimmed_code.rstrip("0") == self.chapter

    @property
    def is_heading(self) -> bool:
        """Returns true if the commodity code represents a HS heading."""
        return self.trimmed_code == self.heading and not self.is_chapter

    @property
    def is_subheading(self) -> bool:
        """Returns true if the commodity code represents a HS subheading."""
        return self.trimmed_code == self.subheading

    @property
    def is_cn_subheading(self) -> bool:
        """Returns true if the commodity code represents a CN subheading."""
        return self.trimmed_code == self.cn_subheading

    @property
    def is_taric_subheading(self) -> bool:
        """Returns true if the commodity code represents a Taric subheading."""
        return self.trimmed_code == self.code

    @property
    def identifier_key(self) -> str:
        """Returns an override of the model identifier_key property."""
        return "key"

    @property
    def identifier(self) -> str:
        """Returns an override of the model instance identifier property."""
        code = self.dot_code
        extra = f"{self.suffix}-{self.get_indent()}/{self.version}"
        return f"{code}-{extra}"

    def get_indent(self) -> int:
        """
        Returns the true indent of the commodity.

        If the indent field of this dataclass has been set, this will take
        precedence over the indent of the wrapped GoodsNomenclature object.
        """
        if self.indent is not None:
            return self.indent

        obj = self.obj.indents.order_by("validity_start").last()

        if obj is None:
            return

        return int(obj.indent)

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

    commodities: List[Commodity]

    def get_commodity(
        self,
        code: str,
        suffix: str = None,
        version: int = None,
        version_group_id: int = None,
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
        code = self._get_sanitized_code(code)
        suffix = suffix or SUFFIX_DECLARABLE

        try:
            return next(
                filter(
                    lambda x: (
                        x.code == code
                        and x.suffix == suffix
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
            return

    def _get_sanitized_code(self, code: str) -> str:
        """Returns the commodity code in GoodsNomenclature.item_id format."""
        code = code.replace(".", "")
        return code + "0" * (10 - len(code))


@dataclass
class SnapshotDiff(BaseModel):
    """
    Provides a construct for CommodityTreeSnapshot diffs.

    The diff construct provides a diff per commodity and relation.
    That is, you can compare across two commodity tree snapshots
    the ancestors, parents, siblings, or children of a given commodity
    and find out how they changed between the two snapshots.

    NOTES:
    1. Calendar vs Transaction Clocks:
    The tariff database uses at least two "clocks":
    - the calendar clock, which revolves around validity dates
    - the transaction clock, which revolves around transaction ids

    A commodity tree snapshot can be taken using
    either the calendar or transaction clock, but not both.
    Accordingly the moment field of this dataclass can be one of:
    - a calendar date (when the type is date)
    - a transaction id (when the type is int)

    2. Use-Case Scenarios for SnapshotDiffs
    There can be a two motivations for getting a diff between snapshots:
    - compare the where a commodity sits in the tree hierarchy
      at two different points in time or as of two different transactions
    - compare the 'before' and 'after' snapshots around a tree update

    For additional context on on snapshots, see the docs for CommodityTreeSnapshot.
    """

    commodity: Commodity
    relation: TreeNodeRelation
    exists: Dict[str, bool]
    values: Dict[str, Union[Commodity, List[Commodity]]]

    @property
    def diff(self) -> List[Commodity]:
        """Returns the diff between the commodity relations across the two
        snapshots."""
        values = [
            [value] if isinstance(value, Commodity) or value is None else value
            for value in self.values.values()
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

    For additional context on commodity trees, see the docs for CommodityTree.
    """

    commodities: List[Commodity]
    clock_type: ClockType
    moment: Union[date, int]
    edges: Dict[str, Commodity] = None

    def __post_init__(self) -> None:
        """
        Builds the commodity tree upon instantiation.

        The business logic for building the tree is as follows:
        - fort the commodities first, and then traverse the sorted collection to build the tree
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
        chapters = {c.chapter for c in self.commodities}

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
        ancestors = []

        current = commodity

        while True:
            parent = self.get_parent(current)
            if parent is None:
                break
            ancestors.append(parent)
            current = parent

        return ancestors[::-1]

    def get_descendants(self, commodity: Commodity) -> List[Commodity]:
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
        if commodity.suffix != SUFFIX_DECLARABLE:
            return False

        return len(self.get_children(commodity)) == 0

    def compare_parents(
        self,
        commodity: Commodity,
        snapshot: "CommodityTreeSnapshot",
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.PARENTS)

    def compare_siblings(
        self,
        commodity: Commodity,
        snapshot: "CommodityTreeSnapshot",
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.SIBLINGS)

    def compare_children(
        self,
        commodity: Commodity,
        snapshot: "CommodityTreeSnapshot",
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.CHILDREN)

    def compare_ancestors(
        self,
        commodity: Commodity,
        snapshot: "CommodityTreeSnapshot",
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.ANCESTORS)

    def compare_descendants(
        self,
        commodity: Commodity,
        snapshot: "CommodityTreeSnapshot",
    ) -> SnapshotDiff:
        return self._get_diff(commodity, snapshot, TreeNodeRelation.DESCENDANTS)

    @property
    def snapshot_date(self) -> date:
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
                x.code,
                x.suffix,
                x.indent,
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
        snapshot: "CommodityTreeSnapshot",
        relation: TreeNodeRelation,
    ) -> SnapshotDiff:
        """
        Returns a snapshot diff for a given relation on a sinlge commodity.

        For detailed overview on snapshot diffs, see the docs for the SnapshotDiff class.

        You can get one diff per commodity and relation type
        (e.g. diff the children of '9999.20.00.00' or diff the siblings of '9999.30.20.10')
        """
        if snapshot == self:
            raise ValueError("The two snapshots are identical.")

        if snapshot.clock_type != self.clock_type:
            raise ValueError("Cannot diff snapshots with different clock types.")

        exists = {
            self.identifier: commodity in self.commodities,
            snapshot.identifier: commodity in snapshot.commodities,
        }

        if relation == TreeNodeRelation.PARENTS:
            attr = "get_parent"
        elif relation == TreeNodeRelation.SIBLINGS:
            attr = "get_siblings"
        elif relation == TreeNodeRelation.CHILDREN:
            attr = "get_children"
        elif relation == TreeNodeRelation.ANCESTORS:
            attr = "get_ancestors"
        elif relation == TreeNodeRelation.DESCENDANTS:
            attr = "get_descendants"
        else:
            raise ValueError("Unknown relation")

        values = {
            self.identifier: getattr(self, attr)(commodity),
            snapshot.identifier: getattr(snapshot, attr)(commodity),
        }

        return SnapshotDiff(
            commodity=commodity,
            relation=relation,
            exists=exists,
            values=values,
        )

    def __eq__(self, snapshot: "CommodityTreeSnapshot") -> bool:
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

    def update(self, changes: Tuple["CommodityChange"]) -> None:
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
        snapshot_date: date = None,
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
        transaction_id: int = None,
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

    def clone(self) -> "CommodityCollection":
        """Returns an independent copy of the collection."""
        return CommodityCollection(self.commodities[:])

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


@dataclass
class SideEffect(BaseModel):
    """
    "Provides a model for commodity change side effects.

    A side effect is simply a pending action taken to preempt a business rule
    violation related to a commodity code change.
    """

    obj: TrackedModel
    update_type: UpdateType
    attrs: Dict[Any, Any] = None


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
    current: Commodity = None
    candidate: Commodity = None
    ignore_validation_rules: bool = False
    side_effects: Dict[Union[str, int], SideEffect] = None

    def __post_init__(self) -> None:
        """Triggers validation on the fields of the model upon instantiation."""
        self.validate()
        self.handle_side_effects()
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
                msg = "The operation is CREATE but no commodity was provided."
                self._handle_validation_issue(msg)

            if candidate is not None:
                msg = (
                    "The operation is CREATE but there is a clash "
                    "with a commodity already exists in the group."
                )
                self._handle_validation_issue(msg)

        else:
            if self.current is None:
                msg = (
                    "The operation is UPDATE or DELETE "
                    "but current commodity was not provied."
                )
                self._handle_validation_issue(msg)

            if current != self.current:
                msg = (
                    "The operation is UPDATE or DELETE "
                    "but there is no matching comodity in the commodity collection."
                )
                self._handle_validation_issue(msg)

        if self.update_type == UpdateType.UPDATE:
            if self.current == self.candidate:
                msg = (
                    "The operation is UPDATE "
                    "but the current and new versions are identical"
                )
                self._handle_validation_issue(msg)

            if candidate == self.candidate:
                msg = (
                    "The operation is UPDATE "
                    "but there is no effective change to the commodity."
                )
                self._handle_validation_issue(msg)

    def handle_side_effects(self) -> None:
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
          there is no need to strict need to invoke them
          when we already know the changing commodity and whether it violates a condition;
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
        if len(self.candidate.trimmed_code) > len(self.current.trimmed_code):
            for measure in good.measures.latest_approved().all():
                try:
                    mbr.ME88().validate(measure)
                except BusinessRuleViolation:
                    self._add_pending_delete(measure)

        # ME71 / NIG18: Invoked from the POV-s of footnote associations
        # here, find all related footnote associations
        # to the commodity as well its measures, and invoke the BR-s
        # (inefficient for this workflow, but consistent use of BR-s)
        if self.candidate.is_taric_subheading is True:
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
            return (
                f"{m.measure_type}."
                f"{m.geographical_area.area_id}."
                f"{m.order_number}."
                f"{m.dead_order_number}."
                f"{m.additional_code}."
                f"{m.dead_additional_code}."
                f"{m.reduction}"
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

        clone = self.collection.clone()
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
            if len(before.compare_parents(child, after).diff) != 0:
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
        key = TrackedModelWrapper(obj=obj).identifier

        self.side_effects[key] = SideEffect(
            obj=obj,
            update_type=UpdateType.DELETE,
        )

    def _add_pending_update(self, obj: TrackedModel, attrs: Dict[Any, Any]) -> None:
        """Add a pending related object update operation to side effects."""
        key = TrackedModelWrapper(obj=obj).identifier

        try:
            self.side_effects[key].attrs.update(attrs)
        except KeyError:
            self.side_effects[key] = SideEffect(
                obj=obj,
                update_type=UpdateType.UPDATE,
                attrs=attrs,
            )

    def _handle_validation_issue(self, msg: str) -> None:
        """Logs a warning message or raises an error."""
        if self.ignore_validation_rules is True:
            logger.warn(msg)
        else:
            raise ValueError(msg)


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

        if current_only is True:
            qs = qs.latest_approved().filter(
                Q(valid_between__endswith=None)
                | Q(valid_between__endswith__gt=date.today()),
            )

        qs = qs.filter(item_id__startswith=self.prefix)

        commodities = [Commodity(obj=obj) for obj in qs.all()]

        return CommodityCollection(commodities=commodities)
