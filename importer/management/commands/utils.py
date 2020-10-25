import logging
import re
from datetime import datetime
from datetime import timedelta
from itertools import combinations
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Generic
from typing import IO
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import TypeVar
from typing import Union

import xlrd
from django.template.loader import render_to_string
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from measures.models import MeasureType

Row = TypeVar("Row")
NewRow = TypeVar("NewRow")
OldRow = TypeVar("OldRow")
ItemIdGetter = Callable[[Row], GoodsNomenclature]

logger = logging.getLogger(__name__)


def maybe_min(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    present = [d for d in objs if d is not None]
    if any(present):
        return min(present)
    else:
        return None


def maybe_max(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    present = [d for d in objs if d is not None]
    if any(present):
        return max(present)
    else:
        return None


def blank(value: Any, convert: Callable[[Any], TypeVar("T")]) -> Optional[TypeVar("T")]:
    return None if value == "" else convert(value)


def col(label: str) -> int:
    """Return the correct index given an Excel column letter."""
    assert len(label) == 1
    return ord(label) - ord("A")


def clean_item_id(cell: Cell) -> str:
    """Given an Excel cell, return a string representing the 10-digit item id
    of a goods nomenclature item taking into account that the cell may
    be storing the item as a number and that trailing zeroes may be missing."""
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
    """Given an Excel cell, return a string representing a duty sentence
    taking into account that the cell may be storing simple percentages
    as a number value."""
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        # This is a percentage value that Excel has
        # represented as a number.
        return f"{cell.value * 100}%"
    else:
        # All other values will apear as text.
        return cell.value


WorkingSetItem = Tuple[GoodsNomenclature, Row, Set[int], bool]


class NomenclatureTreeCollector(Generic[Row]):
    """A working tree is a subtree of the Goods Nomenclature hierarchy
    specified at a certain depth. The first node to be added to the
    Working Set defines the root of the subtree along with some item of
    context. If a child node is added to the Working Set, the root
    is split into smaller subtrees that ensure a complete coverage of
    the original subtree with no overlaps.

    The item of context is normally a row specifying how to subsequently
    create a measure. When the subtree is split, the new child that caused
    the split retains its item of context whereas all of the new children
    inherit their parents context. This ensures that the newly split
    children will have the same measure information as their parent was
    specified with."""

    def __init__(self, date: datetime) -> None:
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
        """Works out whether the passed row links to a commodity code
        that is within the current tree of the others. Returns a bool
        to represent this. Only pushes the row to the buffer if True."""

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
            to_be_split = set(
                parent[0].sid
                for parent, child in combinations(self.roots, 2)
                if self.within_subtree(child[0], parent)
            ) | set(root[0].sid for root in self.roots if root[0].suffix != "80")
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
                        f"Should split parent {parent[0].item_id}/{parent[0].suffix}"
                    )
                    for child_node in (
                        parent[0]
                        .indents.as_at(self.date)
                        .get()
                        .nodes.filter(valid_between__contains=self.date)
                        .get()
                        .get_children()
                        .filter(valid_between__contains=self.date)
                    ):
                        child_cc = child_node.indent.indented_goods_nomenclature
                        if cc != child_cc:
                            self.roots.append(
                                self.make_item(child_cc, parent[1], False)
                            )
                self.roots.sort(
                    key=lambda r: r[0].item_id + r[0].suffix + str(int(r[3]))
                )

    def within_subtree(
        self, cc: GoodsNomenclature, root: WorkingSetItem = None
    ) -> bool:
        """Returns True if the child is a descendant of the passed root, or the
        whole tree if no root is passed."""
        if root is None:
            root = self.root
        return cc == root[0] or cc.sid in root[2]

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
        self, cc: GoodsNomenclature, context: Row, explicit: bool
    ) -> WorkingSetItem:
        return (
            cc,
            context,
            set(
                node.indent.indented_goods_nomenclature.sid
                for node in cc.indents.as_at(self.date)
                .get()
                .nodes.filter(valid_between__contains=self.date)
                .get()
                .get_descendants()
                .filter(valid_between__contains=self.date)
            ),
            explicit,
        )


MeasureDefn = Tuple[List[OldRow], NewRow, GoodsNomenclature]


class MeasureTypeSlicer(Generic[OldRow, NewRow]):
    """Detect which measure types are in the old rows and if many
    measure types are present, generate new measures for each old row.
    If only one measure type is present, generate one measure for it.
    We may have duplicate entries due to Entry Price System but
    we only want one new measure per item id, hence use of sets."""

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
        self, old_rows: List[OldRow], cc: Optional[GoodsNomenclature] = None
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


class SeasonalRateParser:
    SEASONAL_RATE = re.compile(r"([\d\.]+%) *\((\d\d [A-Z]{3}) *- *(\d\d [A-Z]{3})\)")

    def __init__(self, base_date: datetime, timezone) -> None:
        assert base_date.day == 1
        assert base_date.month == 1
        self.base = base_date
        self.timezone = timezone

    def detect_seasonal_rates(self, duty_exp: str) -> Iterable:
        if SeasonalRateParser.SEASONAL_RATE.search(duty_exp):
            for match in SeasonalRateParser.SEASONAL_RATE.finditer(duty_exp):
                rate, start, end = match.groups()
                validity_start = self.timezone.localize(
                    datetime.strptime(start, r"%d %b")
                )
                validity_end = self.timezone.localize(datetime.strptime(end, r"%d %b"))
                if validity_start.month > validity_end.month:
                    # This straddles a year boundary so
                    # we need to make one measure for BREXIT to end
                    # and then another for start to BREXIT+1
                    yield (rate, self.base, validity_end.replace(year=self.base.year))
                    yield (
                        rate,
                        validity_start.replace(year=self.base.year),
                        self.base.replace(year=self.base.year + 1) + timedelta(days=-1),
                    )
                else:
                    # Both months are in one year, hence make them 2021
                    yield (
                        rate,
                        validity_start.replace(year=self.base.year),
                        validity_end.replace(year=self.base.year),
                    )
        else:
            # Non-seasonal rate!
            yield (duty_exp, self.base, None)


Counter = Callable[[], int]


class EnvelopeSerializer:
    """A performant envelope serializer. It does not need to keep
    everything in memory to generate an envelope, instead using
    a streaming approach. Also keeps track of transaction and message IDs."""

    def __init__(
        self,
        output: IO,
        envelope_id: int,
        transaction_counter: Counter = counter_generator(),
        message_counter: Counter = counter_generator(),
    ) -> None:
        self.output = output
        self.transaction_counter = transaction_counter
        self.message_counter = message_counter
        self.envelope_id = envelope_id
        self.serializer = TrackedModelSerializer(context={"format": "xml"})

    def __enter__(self):
        self.output.write(
            render_to_string(
                template_name="common/taric/start_envelope.xml",
                context={"envelope_id": self.envelope_id},
            )
        )
        return self

    def __exit__(self, *_) -> None:
        self.output.write(
            render_to_string(template_name="common/taric/end_envelope.xml")
        )

    def render_transaction(self, models: List[TrackedModel]) -> None:
        if any(models):
            self.output.write(
                render_to_string(
                    template_name="workbaskets/taric/transaction.xml",
                    context={
                        "tracked_models": map(
                            self.serializer.to_representation, models
                        ),
                        "transaction_id": self.transaction_counter(),
                        "counter_generator": counter_generator,
                        "message_counter": self.message_counter,
                    },
                )
            )
