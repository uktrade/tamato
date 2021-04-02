import logging
from datetime import date
from functools import cached_property
from typing import Generic
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union

import pytz
import xlrd
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from importer.management.commands.utils import MeasureContext
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import blank
from importer.management.commands.utils import clean_item_id

logger = logging.getLogger(__name__)

# The timezone of GB.
LONDON = pytz.timezone("Europe/London")

# The date of the end of the transition period,
# localized to the Europe/London timezone.
BREXIT = date(2021, 1, 1)


def parse_date(cell: Cell) -> date:
    if cell.ctype == xlrd.XL_CELL_DATE:
        return LONDON.localize(
            xlrd.xldate.xldate_as_datetime(cell.value, datemode=0),
        ).date()
    return date.fromisoformat(cell.value)


def parse_list(value: str) -> List[str]:
    return list(filter(lambda s: s != "", map(str.strip, value.split(","))))


class OldMeasureRow:
    def __init__(self, old_row: List[Cell]) -> None:
        assert old_row is not None
        self.goods_nomenclature_sid = int(old_row[0].value)
        self.item_id = clean_item_id(old_row[1])
        self.inherited_measure = bool(old_row[6].value)
        assert not self.inherited_measure, "Old row should not be an inherited measure"
        self.measure_sid = int(old_row[7].value)
        self.measure_type = str(int(old_row[8].value))
        self.geo_sid = int(old_row[13].value)
        self.measure_start_date = parse_date(old_row[16])
        self.measure_end_date = blank(
            old_row[17].value,
            lambda _: parse_date(old_row[17]),
        )
        self.regulation_role = int(old_row[18].value)
        self.regulation_id = str(old_row[19].value)
        self.order_number = blank(old_row[15].value, str)
        self.justification_regulation_role = blank(old_row[20].value, int)
        self.justification_regulation_id = blank(old_row[21].value, str)
        self.stopped = bool(old_row[24].value)
        self.additional_code_sid = blank(old_row[23].value, int)
        self.export_refund_sid = blank(old_row[25].value, int)
        self.reduction = blank(old_row[26].value, int)
        self.footnotes = parse_list(old_row[27].value)
        self.goods_nomenclature = GoodsNomenclature.objects.get(
            sid=self.goods_nomenclature_sid,
        )

    @cached_property
    def additional_code(self) -> Optional[AdditionalCode]:
        codes = AdditionalCode.objects.filter(sid=self.additional_code_sid).all()
        return codes[0] if any(codes) else None

    @cached_property
    def measure_context(self) -> MeasureContext:
        return MeasureContext(
            self.measure_type,
            self.geo_sid,
            self.additional_code.type.sid if self.additional_code else None,
            self.additional_code.code if self.additional_code else None,
            self.order_number,
            self.reduction,
            self.measure_start_date,
            self.measure_end_date,
        )


OldRow = TypeVar("OldRow")
NewRow = TypeVar("NewRow")
OldContext = Union[
    NomenclatureTreeCollector[OldRow],
    NomenclatureTreeCollector[List[OldRow]],
]
NewContext = Union[
    NomenclatureTreeCollector[NewRow],
    NomenclatureTreeCollector[List[NewRow]],
]


def add_single_row(tree: NomenclatureTreeCollector[OldRow], row: OldRow) -> bool:
    return tree.add(row.goods_nomenclature, context=row)


def add_multiple_row(
    tree: NomenclatureTreeCollector[List[OldRow]],
    row: OldRow,
) -> bool:
    if row.goods_nomenclature in tree:
        roots = [root for root in tree.buffer() if root[0] == row.goods_nomenclature]
        assert len(roots) == 1
        logger.debug(
            "Adding to old context (len %s) when adding cc %s [%s]",
            len(roots[0][1]),
            row.goods_nomenclature.item_id,
            row.goods_nomenclature.sid,
        )
        context = [*roots[0][1], row]
    else:
        logger.debug(
            "Ignoring old context when adding cc %s [%s]",
            row.goods_nomenclature.item_id,
            row.goods_nomenclature.sid,
        )
        context = [row]
    return tree.add(row.goods_nomenclature, context=context)


class DualRowRunner(Generic[OldRow, NewRow]):
    def __init__(
        self,
        old_rows: OldContext,
        new_rows: NewContext,
        add_old_row=add_multiple_row,
        add_new_row=add_single_row,
    ) -> None:
        self.old_rows = old_rows
        self.new_rows = new_rows
        self.add_old_row = add_old_row
        self.add_new_row = add_new_row

    def handle_rows(
        self,
        old_row: Optional[OldRow],
        new_row: Optional[NewRow],
    ) -> Iterator[None]:
        logger.debug(
            "Have old row for GN: %s. Have new row for GN: %s",
            old_row.goods_nomenclature.sid
            if old_row is not None and old_row.goods_nomenclature is not None
            else None,
            new_row.goods_nomenclature.sid
            if new_row is not None and new_row.goods_nomenclature is not None
            else None,
        )

        # Push the new row into the tree, but only if a CC is found for it
        # Initialize the old row tree with the same subtree if it is not yet set
        if new_row is not None and new_row.goods_nomenclature is not None:
            new_waiting = not self.add_new_row(self.new_rows, new_row)
        else:
            new_waiting = False

        if self.old_rows.root is None:
            self.old_rows.root = self.new_rows.root

        # Push the old row into the tree, adding to any rows already for this CC
        # Initialize the new row tree with the same subtree if it is not yet set
        if old_row is not None and old_row.goods_nomenclature is not None:
            old_waiting = not self.add_old_row(self.old_rows, old_row)
        else:
            old_waiting = False

        if self.new_rows.root is None:
            self.new_rows.root = self.old_rows.root

        if old_waiting or new_waiting:
            # A row was rejected by the collector
            # The collector is full and the row should be processed
            logger.debug(
                f"Collector full with {len(self.old_rows.roots)} old (waiting {old_waiting})"
                f" and {len(self.new_rows.roots)} new (waiting {new_waiting})",
            )
            yield

            self.old_rows.reset()
            self.new_rows.reset()
            yield from self.handle_rows(
                old_row if old_waiting else None,
                new_row if new_waiting else None,
            )
        else:
            return iter([])
