import argparse
import logging
import re
from collections import namedtuple
from datetime import date
from decimal import Decimal
from itertools import combinations
from math import floor
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import TypeVar
from typing import Union
from typing import cast

import xlrd
from django.contrib.auth.models import User
from django.core.management.base import CommandError
from xlrd.sheet import Cell

import settings
from commodities.models import GoodsNomenclature
from common.renderers import counter_generator
from measures.models import MeasureType

Row = TypeVar("Row")
NewRow = TypeVar("NewRow")
OldRow = TypeVar("OldRow")
ItemIdGetter = Callable[[Row], GoodsNomenclature]

logger = logging.getLogger(__name__)


class CountersAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string=None,
    ) -> None:
        counters = getattr(namespace, "counters", {})
        setattr(namespace, "counters", {self.dest: values, **counters})


def id_argument(parser: Any, name: str, default: Optional[int] = None) -> None:
    parser.add_argument(
        f"--{name}-id",
        help=f"The ID value to use for the first new {(name.replace('-', ''))}.",
        type=lambda s: counter_generator(int(s)),
        action=CountersAction,
        default=default,
    )


def spreadsheet_argument(parser: Any, name: str) -> None:
    parser.add_argument(
        f"{name}-spreadsheet",
        help=f"The XLSX file containing new {name}s to be parsed.",
        type=str,
    )
    parser.add_argument(
        f"--{name}-skip-rows",
        help="The number of rows from the spreadsheet to skip before importing data",
        type=int,
        default=0,
    )


def output_argument(parser: Any) -> None:
    parser.add_argument(
        "--output",
        help="The filename to output to.",
        type=str,
        default="out.xml",
    )


def blank(value: Any, convert: Callable[[Any], TypeVar("T")]) -> Optional[TypeVar("T")]:
    return None if value == "" else convert(value)


def col(label: str) -> int:
    """Return the correct index given an Excel column letter."""
    assert len(label) in [1, 2]
    multiple = ord(label[0]) - ord("A") + 1 if len(label) > 1 else 0
    index = (ord(label[1]) if len(label) > 1 else ord(label[0])) - ord("A")
    return multiple * 26 + index


def clean_regulation(cell: Cell) -> str:
    regulation_id = str(cell.value)
    formats = [
        r"Regulation (?P<part1>\d{4})/(?P<part2>\d{2})$",
        r"Decision (?P<part1>\d{4})/(?P<part2>\d{2})$",
        r"Information (?P<part1>\d{4})/(?P<part2>\d{2})$",
        r"R\d{6}0$",
    ]
    match, match_id = None, None
    for i, format in enumerate(formats):
        match = re.match(format, regulation_id)
        if match:
            match_id = i
            break
    if match_id in [0, 1, 2]:
        part1 = match.group("part1")
        part2 = match.group("part2")
        return f"R{part2}{part1}0"
    elif match_id == 3:
        return regulation_id
    raise ValueError("Unknown regulation")


Expression = namedtuple("Expression", "condition component")
condition_fields = (
    "condition_code",
    "certificate",
    "certificate_type_code",
    "certificate_code",
    "action_code",
)
Condition = namedtuple(
    "Condition",
    condition_fields,
    defaults=(None,) * len(condition_fields),
)
component_fields = (
    "duty_expression_id",
    "duty_amount",
    "monetary_unit_code",
    "measurement_unit_code",
    "measurement_unit_qualifier_code",
)
Component = namedtuple(
    "Component",
    component_fields,
    defaults=(None,) * len(condition_fields),
)


def parse_trade_remedies_duty_expression(
    value: str,
    eur_gbp_conversion_rate: float = None,
) -> List[Expression]:
    """
    Parse duty expression as expressions with conditions and components:

    - Measure conditions
        c1: condition.code
        c2: requires certificate?
        c3: certificate.type.code
        c4: certificate.code
        c5: action.code (always 01 - apply the amount of the action)

    - Measure components (only 1):
        m1: duty.expression.id (01 or 37 if NIHIL)
        m2: duty.amount
        m3: monetary.unit.code
        m4: measurement.unit.code
        m5: measurement.unit.qualifier.code

    Examples:
    - Cond:  A cert: D-008 (01):0.000 EUR TNE I ; A (01):172.200 EUR TNE I
        c1: A      m1: 01
        c2: True   m2: 0.000
        c3: D      m3: EUR
        c4: 008    m4: TNE
        c5: 01     m5: I

        c1: A      m1: 01
        c2: False  m2: 172.200
        c3: N/A    m3: EUR
        c4: N/A    m4: TNE
        c5: 01     m5: I

    Cond:  A cert: D-017 (01):0.000 % ; A cert: D-018 (01):28.200 % ; A (01):28.200 %
        c1: A      m1: 01
        c2: True   m2: 0.000
        c3: D      m3: N/A
        c4: 017    m4: N/A
        c5: 01     m5: N/A

        c1: A      m1: 01
        c2: True   m2: 28.200
        c3: D      m3: N/A
        c4: 018    m4: N/A
        c5: 01     m5: N/A

        c1: A      m1: 01
        c2: False  m2: 28.200
        c3: N/A    m3: N/A
        c4: N/A    m4: N/A
        c5: 01     m5: N/A
    """

    def create_component(match):
        return Component(
            duty_expression_id="37" if match.group("m1") == "NIHIL" else "01",
            duty_amount=convert_eur_to_gbp(match.group("m2"), eur_gbp_conversion_rate)
            if match.group("m3") == "EUR" and eur_gbp_conversion_rate
            else match.group("m2"),
            monetary_unit_code="GBP"
            if match.group("m3") == "EUR" and eur_gbp_conversion_rate
            else match.group("m3"),
            measurement_unit_code=match.group("m4"),
            measurement_unit_qualifier_code=match.group("m5"),
        )

    if value.startswith("Cond: "):
        regex = (
            r"^(?P<c1>[A-Z]) (?:(?P<c2>cert:) (?P<c3>[A-Z])-(?P<c4>\d{3}) )?\((?P<c5>\d{2})\):"
            r"(?:(?P<m1>NIHIL)(?:$)|(?P<m2>\S+)(?:\s|$))(?:(?P<m3>\S+)(?:\s|$))?(?:(?P<m4>\S+)(?:\s|$))?"
            r"(?:(?P<m5>\S+)(?:\s|$))?"
        )
        parsed_expressions = []
        for entry in value.lstrip("Cond: ").split(";"):
            entry = entry.strip()
            match = re.match(regex, entry)
            if match:
                condition = Condition(
                    condition_code=match.group("c1"),
                    certificate=match.group("c2") == "cert:",
                    certificate_type_code=match.group("c3"),
                    certificate_code=match.group("c4"),
                    action_code=match.group("c5"),
                )
                expression = Expression(
                    condition=condition,
                    component=create_component(match),
                )
                parsed_expressions.append(expression)
            else:
                raise ValueError(f"Could not parse duty expression: {value}")
    else:
        regex = (
            r"^(?:(?P<m1>NIHIL)(?:$)|(?P<m2>\S+)(?:\s|$))(?:(?P<m3>\S+)(?:\s|$))?(?:(?P<m4>\S+)(?:\s|$))?"
            r"(?:(?P<m5>\S+)(?:\s|$))?"
        )
        parsed_expressions = []
        entry = value.strip()
        match = re.match(regex, entry)
        if match:
            expression = Expression(
                condition=None,
                component=create_component(match),
            )
            parsed_expressions.append(expression)
        else:
            raise ValueError(f"Could not parse duty expression: {value}")
    return parsed_expressions


def convert_eur_to_gbp(amount: str, conversion_rate: float) -> str:
    """Convert EUR amount to GBP and round down to nearest pence."""
    converted_amount = (
        floor(int(Decimal(amount) * Decimal(conversion_rate) * 100)) / 100
    )
    return "{0:.3f}".format(converted_amount)


def clean_item_id(cell: Cell) -> str:
    """Given an Excel cell, return a string representing the 10-digit item id of
    a goods nomenclature item taking into account that the cell may be storing
    the item as a number and that trailing zeroes may be missing."""
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        item_id = str(int(cell.value))
    else:
        item_id = str(cell.value)

    if len(item_id) % 2 == 1:
        # If we have an odd number of digits its because
        # we lost a leading zero due to the numeric storage
        item_id = "0" + item_id

    # We need a full 10 digit code so padd with trailing zeroes
    assert len(item_id) % 2 == 0
    if len(item_id) == 8:
        item_id += "00"

    assert len(item_id) == 10
    return item_id


def clean_duty_sentence(cell: Cell) -> str:
    """Given an Excel cell, return a string representing a duty sentence taking
    into account that the cell may be storing simple percentages as a number
    value."""
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        # This is a percentage value that Excel has
        # represented as a number.
        return f"{cell.value * 100}%"
    else:
        # All other values will apear as text.
        return cell.value


def get_author(username: Optional[str] = None) -> User:
    username = username or settings.DATA_IMPORT_USERNAME
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        raise CommandError(
            f"Author does not exist, create user '{username}'"
            " or edit settings.DATA_IMPORT_USERNAME",
        )


WorkingSetItem = Tuple[GoodsNomenclature, Row, Set[int], bool]


class NomenclatureTreeCollector(Generic[Row]):
    """
    A working tree is a subtree of the Goods Nomenclature hierarchy specified at
    a certain depth. The first node to be added to the Working Set defines the
    root of the subtree along with some item of context. If a child node is
    added to the Working Set, the root is split into smaller subtrees that
    ensure a complete coverage of the original subtree with no overlaps.

    The item of context is normally a row specifying how to subsequently create
    a measure. When the subtree is split, the new child that caused the split
    retains its item of context whereas all of the new children inherit their
    parents context. This ensures that the newly split children will have the
    same measure information as their parent was specified with.
    """

    def __init__(self, date: date) -> None:
        self.reset()
        self.date = date

    def reset(self) -> None:
        self.root = cast(WorkingSetItem, None)
        self.roots = cast(List[WorkingSetItem], [])

    def __contains__(self, cc: GoodsNomenclature) -> bool:
        for root in self.roots:
            if root[0] == cc:
                return True
        return False

    def add(self, cc: GoodsNomenclature, context: Optional[Row] = None) -> bool:
        """
        Works out whether the passed row links to a commodity code that is
        within the current tree of the others.

        Returns a bool to represent this. Only pushes the row to the buffer if
        True.
        """

        # If we have not specified a root yet, (this is the first item),
        # then set the root up. All future stored children will be
        # descendants of this root.
        if self.root is None:
            assert context is not None
            item = self.make_item(cc, context, True)
            self.root = item

        else:
            # Is the given CC a descendant of the root? If not, we ignore it.
            if not self.within_subtree(cc):
                return False

            # If the context is None, we are adding a child to the tree and
            # specifying that it should take the context from it's parent. So go and
            # discover that parent to work out the right context.
            if context is None:
                parent = [root for root in self.roots if self.within_subtree(cc, root)]
                assert len(parent) == 1, f"{len(parent)} parents for {cc}"
                context = parent[0][1]

            item = self.make_item(cc, context, True)

        # We will add the CC to the tree. We need to split the tree so that
        # there are no overlaps. We keep the roots sorted so that we can call
        # combinations below and process less pairs.
        self.roots.append(item)
        self.roots.sort(key=lambda r: r[0].item_id + r[0].suffix + str(int(r[3])))

        while True:
            # Find all the CCs that overlap with the passed child
            # and break them down until there are no overlaps anymore.
            # Make sure all codes are actually declarable (suffix 80)
            # otherwise we break ME7.
            to_be_split = self.to_be_split() | set(
                root[0].sid for root in self.roots if root[0].suffix != "80"
            )
            if not any(to_be_split):
                return True

            for parent in (root for root in self.roots if root[0].sid in to_be_split):
                self.roots.remove(parent)
                if parent[0] == cc and cc.suffix == "80":
                    # We are adding a child that is already present
                    # We have removed the old already and added the new already
                    pass
                else:
                    logger.debug(
                        f"Should split parent {parent[0].item_id}/{parent[0].suffix}",
                    )
                    for child_node in (
                        parent[0]
                        .indents.as_at(self.date)
                        .get()
                        .nodes.get(valid_between__contains=self.date)
                        .get_children()
                        .filter(valid_between__contains=self.date)
                    ):
                        child_cc = child_node.indent.indented_goods_nomenclature
                        if cc != child_cc:
                            self.roots.append(
                                self.make_item(child_cc, parent[1], False),
                            )
                self.roots.sort(
                    key=lambda r: r[0].item_id + r[0].suffix + str(int(r[3])),
                )

    def within_subtree(
        self,
        cc: GoodsNomenclature,
        root: WorkingSetItem = None,
    ) -> bool:
        """Returns True if the child is a descendant of the passed root, or the
        whole tree if no root is passed."""
        if root is None:
            root = self.root
        return cc == root[0] or cc.sid in root[2]

    def to_be_split(self) -> Set[int]:
        return set(
            parent[0].sid
            for parent, child in combinations(self.roots, 2)
            if self.within_subtree(child[0], parent)
        )

    def is_split_beyond(self, cc: GoodsNomenclature) -> bool:
        """Returns True if the subtree has already been split to a depth beyond
        the passed commodity code."""
        if not self.within_subtree(cc):
            return False

        # We know the cc is contained in this tree. We check to see if the cc is
        # contained with anybody's descendants list. If so, we are not yet
        # sufficiently split. If not, we must have already split the roots.
        return not any(cc.sid in root[2] for root in self.roots)

    def buffer(self) -> Iterator[Tuple[GoodsNomenclature, Row]]:
        return ((root[0], root[1]) for root in self.roots)

    def make_item(
        self,
        cc: GoodsNomenclature,
        context: Row,
        explicit: bool,
    ) -> WorkingSetItem:
        return (
            cc,
            context,
            set(
                node.indent.indented_goods_nomenclature.sid
                for node in cc.indents.as_at(self.date)
                .get()
                .nodes.get(valid_between__contains=self.date)
                .get_descendants()
                .filter(valid_between__contains=self.date)
            ),
            explicit,
        )


# ME32: Measure type, geo sid, add type, add code, order number, reduction
class MeasureContext:
    def __init__(
        self,
        measure_type: str,
        geographical_area_sid: int,
        additional_code_type: Optional[str],
        additional_code_body: Optional[str],
        order_number: Optional[str],
        reduction_indicator: Optional[int],
        start_date: date,
        end_date: Optional[date],
    ) -> None:
        self.equal_fields = (
            measure_type,
            geographical_area_sid,
            additional_code_type,
            additional_code_body,
            order_number,
            reduction_indicator,
        )
        self.start_date = start_date
        self.end_date = end_date

    def overlaps(self, other) -> bool:
        # self: [-------]
        # other:     [-------]
        # self:    [------]
        # other: [----------->
        # self:     [-------->
        # other: [----]
        return (
            self.equal_fields == other.equal_fields
            and (self.start_date <= other.end_date if other.end_date else True)
            and (self.end_date >= other.start_date if self.end_date else True)
        )


class MeasureTreeCollector(Generic[Row], NomenclatureTreeCollector[Row]):
    def add(self, cc: GoodsNomenclature, context: Optional[Row]) -> bool:
        losers = (
            root
            for root in self.roots
            if root[0] == cc
            and root[1].measure_context.overlaps(context.measure_context)
        )
        if any(losers):
            logger.warning("About to overwrite context for %s[%s]", cc, cc.sid)

        return super().add(cc, context)

    def to_be_split(self) -> Set[int]:
        return set(
            parent[0].sid
            for parent, child in combinations(self.roots, 2)
            if self.within_subtree(child[0], parent)
            and parent[1].measure_context.overlaps(child[1].measure_context)
        )


MeasureDefn = Tuple[List[OldRow], NewRow, GoodsNomenclature]


class MeasureTypeSlicer(Generic[OldRow, NewRow]):
    """
    Detect which measure types are in the old rows and if many measure types are
    present, generate new measures for each old row.

    If only one measure type is present, generate one measure for it. We may
    have duplicate entries due to Entry Price System but we only want one new
    measure per item id, hence use of sets.
    """

    def __init__(
        self,
        get_old_measure_type: Callable[[OldRow], MeasureType],
        get_goods_nomenclature: Callable[[Union[OldRow, NewRow]], GoodsNomenclature],
        default_measure_type: MeasureType = None,
    ) -> None:
        self.get_old_measure_type = get_old_measure_type
        self.get_goods_nomenclature = get_goods_nomenclature
        self.default_measure_type = default_measure_type

    def sliced_new_rows(
        self,
        old_rows: NomenclatureTreeCollector[List[OldRow]],
        new_rows: NomenclatureTreeCollector[NewRow],
    ) -> Iterable[MeasureDefn]:
        # First we need to work out if there is any measure type split
        # in the old row subtree. If not, we can just apply the same measure
        # type to all of the new rows.
        item_ids = cast(Dict[GoodsNomenclature, List[OldRow]], {})
        for cc, rows in old_rows.buffer():
            # We should not have the same item ID appearing in two sets
            assert cc not in item_ids
            item_ids[cc] = rows

        measure_types = set(
            self.get_old_measure_type(o) for rows in item_ids.values() for o in rows
        )
        if len(measure_types) < 1 and self.default_measure_type:
            single_type = self.default_measure_type
        elif len(measure_types) < 1 and not self.default_measure_type:
            raise Exception("No measure types found and no default set")
        elif len(measure_types) == 1:
            single_type = measure_types.pop()
        else:
            # There is more than one type
            single_type = None

        if not single_type:
            # There is a split of measure types across the old rows
            # First we will push old rows into the new tree to make sure the
            # tree is sufficiently split, and then we will look up the measure
            # type in the dictionary for each new row. The new rows might be
            # descendants of the old rows so we check for that too.
            for cc, many_old_row in old_rows.buffer():
                if not new_rows.is_split_beyond(cc):
                    new_rows.add(cc)

        # Now create the new rows as desired
        for cc, new_row in new_rows.buffer():
            if cc in item_ids:
                matched_old_rows = item_ids[cc]
            else:
                ancestor_cc = [
                    root[0]
                    for root in old_rows.roots
                    if old_rows.within_subtree(cc, root)
                ]
                assert (
                    len(ancestor_cc) <= 1
                ), f"Looking for: {cc.item_id}[{cc.sid}], found {len(ancestor_cc)}"
                if len(ancestor_cc) == 1:
                    matched_old_rows = item_ids[ancestor_cc[0]]
                else:
                    matched_old_rows = []

            yield matched_old_rows, new_row, cc

    def get_measure_type(
        self,
        old_rows: List[OldRow],
        cc: Optional[GoodsNomenclature] = None,
    ) -> MeasureType:
        measure_types = set(self.get_old_measure_type(r) for r in old_rows)
        assert len(measure_types) <= 1, f"{len(measure_types)} for rows {old_rows}"
        if len(measure_types) == 1:
            return measure_types.pop()
        elif self.default_measure_type:
            logger.warning(
                "No old rows found for CC '%s' so using type %s",
                cc,
                self.default_measure_type,
            )
            return self.default_measure_type
        else:
            raise Exception("No measure types found and no default set")
