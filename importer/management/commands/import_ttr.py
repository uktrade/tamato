# WIP script to import TTR rates in case of no deal

import logging
import sys
from datetime import timedelta
from typing import Callable, Generic, TypeVar
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import LONDON
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, MeasureDefn
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import SeasonalRateParser
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)
NewRow = TypeVar("NewRow")
OldRow = TypeVar("OldRow")


class TTRRow:
    def __init__(self, new_row: List[Cell]) -> None:
        assert new_row is not None
        cn8 = new_row[col("A")]
        cn10 = new_row[col("B")]
        item_id = cn10 if cn10.value else cn8
        self.item_id = clean_item_id(item_id)
        self.ttr_rate = str(new_row[col("C")].value)
        self.measure_type = '112'

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            self.goods_nomenclature = None


class TTRSlicer(Generic[OldRow, NewRow]):
    """Detect which measure types are in the old rows and if many
    measure types are present, generate new measures for each old row.
    If only one measure type is present, generate one measure for it.
    We may have duplicate entries due to Entry Price System but
    we only want one new measure per item id, hence use of sets."""

    def __init__(
        self,
        get_old_measure_type: Callable[[OldRow], MeasureType],
        get_goods_nomenclature: Callable[[Union[OldRow, TTRRow]], GoodsNomenclature],
    ) -> None:
        self.get_old_measure_type = get_old_measure_type
        self.get_goods_nomenclature = get_goods_nomenclature

    def sliced_new_rows(
        self,
        old_rows: NomenclatureTreeCollector[List[OldRow]],
        new_rows: NomenclatureTreeCollector[TTRRow],
    ) -> Iterable[MeasureDefn]:
        # First we need to work out if there is any measure type split
        # in the old row subtree. If not, we can just apply the same measure
        # type to all of the new rows.
        item_ids: Dict[GoodsNomenclature, List[OldRow]] = {}
        for cc, rows in old_rows.buffer():
            # We should not have the same item ID appearing in two sets
            assert cc not in item_ids
            item_ids[cc] = rows

        measure_types = set(
            self.get_old_measure_type(o) for rows in item_ids.values() for o in rows
        )
        #duty_rate = set(
        #    self.get_old_duty_rate(o) for rows in item_ids.values() for o in rows
        #)

        # Look at old measure types
        if len(measure_types) < 1:
            raise Exception("No measure types found in old rows")
        elif len(measure_types) == 1:
            single_type = measure_types.pop()
        else:
            # There is more than one type
            single_type = None

        # Look at old duty rates

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


class TTRImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {
            str(m.sid): m
            for m in [
                MeasureType.objects.get(sid="112"),
                MeasureType.objects.get(sid="115"),
            ]
        }
        self.measure_slicer = TTRSlicer[OldMeasureRow, TTRRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
        )
        self.seasonal_rate_parser = SeasonalRateParser(BREXIT, LONDON)

        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[TTRRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)

        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)

        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.suspensions_si = Regulation.objects.get(
            regulation_id="C2100003"
        )
        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.suspensions_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_sid_counter"],
        )
        return []

    def handle_row(
        self,
        new_row: Optional[TTRRow],
        old_row: Optional[OldMeasureRow],
    ) -> Iterator[List[TrackedModel]]:
        for _ in self.row_runner.handle_rows(old_row, new_row):
            for transaction in self.flush():
                yield transaction

    def flush(self) -> Iterator[List[TrackedModel]]:
        # get new measure properties
        old_sids = set()
        for (
            matched_old_rows,
            new_row,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(self.old_rows, self.new_rows):
            new_measure = self.get_new_measure(
                new_row, goods_nomenclature
            )
            # check duty rate
            if new_measure['duty_sentence'] < clean_duty_sentence(row.duty_expression):
                for row in matched_old_rows:
                    if row.measure_sid in old_sids:
                        continue
                    old_sids.add(row.measure_sid)
                    logger.debug("End-dating matched measure: %s", row.measure_sid)
                    yield list(
                        self.measure_ender.end_date_measure(row, self.suspensions_si)
                    )

                if row.measure_sid in old_sids:
                    continue
                old_sids.add(row.measure_sid)
                assert (
                    row.measure_type in self.measure_types
                ), f"{row.measure_type} not in {self.measure_types}"
                assert row.order_number is None
                assert row.geo_sid == self.erga_omnes.sid
                if row.goods_nomenclature_sid == new_measure['goods_nomenclature'].sid \
                    and row.geo_sid == new_measure['geography'].sid \
                    and clean_duty_sentence(row.duty_expression) == new_measure['duty_sentence'] \
                    and row.measure_type == new_measure['new_measure_type'].sid \
                    and row.measure_start_date == new_measure['validity_start'] \
                    and row.measure_end_date == new_measure['validity_end'] \
                    and set(row.footnotes) == set([str(f) for f in new_measure['footnotes']]):
                    logger.debug(f'Matching measure found for cc {row.measure_sid}')
                    match_found = True
                else:
                    logger.debug("End-dating matched measure: %s", row.measure_sid)
                    yield list(
                        self.measure_ender.end_date_measure(row, self.suspensions_si)
                    )

            # Create measures either for the single measure type or a mix
            if not match_found:
                yield list(
                    self.measure_creator.create(**new_measure)
                )

    def get_new_measure(
        self,
        new_row: TTRRow,
        goods_nomenclature: GoodsNomenclature,
    ) -> Iterator[List[TrackedModel]]:
        return {
            'duty_sentence': clean_duty_sentence(new_row.ttr_rate),
            'geography': self.erga_omnes,
            'goods_nomenclature': goods_nomenclature,
            'new_measure_type': self.measure_types[new_row.measure_type],
            'validity_start': BREXIT,
            'validity_end': BREXIT.replace(year=2022) - timedelta(days=1),
        }


class Command(BaseCommand):
    help = "Merge TTR and suspensions"

    def add_arguments(self, parser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file containing measures to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
        )
        parser.add_argument(
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
        )
        parser.add_argument(
            "--output", help="The filename to output to.", type=str, default="out.xml"
        )

    def handle(self, *args, **options):
        username = settings.DATA_IMPORT_USERNAME
        try:
            author = User.objects.get(username=username)
        except User.DoesNotExist:
            sys.exit(
                f"Author does not exist, create user '{username}'"
                " or edit settings.DATA_IMPORT_USERNAME"
            )
        workbook = xlrd.open_workbook(options["spreadsheet"])
        existing_uk_suspensions = workbook.sheet_by_name("existing_uk_suspensions")
        final_uk_ttr = workbook.sheet_by_name("final_uk_ttr")

        existing_uk_suspensions = existing_uk_suspensions.get_rows()
        final_uk_ttr = final_uk_ttr.get_rows()
        for _ in range(1):
            next(final_uk_ttr)
            next(existing_uk_suspensions)

        new_rows = [TTRRow(row) for row in list(final_uk_ttr)]
        new_rows.sort(key=lambda row: row.item_id)
        old_rows = [
            OldMeasureRow(row) for row in list(
                existing_uk_suspensions
            )
        ]
        old_rows.sort(key=lambda row: row.item_id)

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Temporary Tariff Rates",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )
        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                    output,
                    envelope_id=options["envelope_id"],
                    transaction_counter=counter_generator(options["transaction_id"]),
                    message_counter=counter_generator(start=1),
                    max_envelope_size_in_mb=40,
            ) as env:
                importer = TTRImporter(
                    workbasket,
                    env,
                )
                importer.counters["measure_sid_counter"] = counter_generator(options["measure_sid"])
                importer.import_sheets(
                    new_rows,
                    old_rows,
                )
