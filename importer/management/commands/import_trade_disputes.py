import logging
import sys
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import LONDON
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import SeasonalRateParser
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        self.item_id = clean_item_id(new_row[col("B")])
        self.duty_rate = new_row[col("D")]

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist:
            logger.warning(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            self.goods_nomenclature = None


class TradeDisputesImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {695: MeasureType.objects.get(sid="695")}
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
            default_measure_type=MeasureType.objects.get(sid="695"),
        )
        self.seasonal_rate_parser = SeasonalRateParser(BREXIT, LONDON)
        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[NewRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.geo_area = GeographicalArea.objects.as_at(BREXIT).get(sid=103)
        self.generating_regulation, _ = Regulation.objects.get_or_create(
            regulation_id="C2100004",
            regulation_group=Group.objects.get(group_id="ADD"),
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.generating_regulation
        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )
        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.generating_regulation,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )

    def handle_row(
        self,
        new_row: Optional[NewRow],
        old_row: Optional[OldMeasureRow],
    ) -> Iterator[List[TrackedModel]]:
        for _ in self.row_runner.handle_rows(old_row, new_row):
            for transaction in self.flush():
                yield transaction

    def flush(self) -> Iterator[List[TrackedModel]]:
        # Send the old row to be end dated or removed
        old_sids = set()
        for cc, rows in self.old_rows.buffer():
            assert len(rows) >= 1
            for row in rows:
                assert (
                    row.measure_sid not in old_sids
                ), f"Measure appears more than once: {row.measure_sid}"
                old_sids.add(row.measure_sid)

                assert (
                    row.measure_type in self.measure_types
                ), f"{row.measure_type} not in {self.measure_types}"
                assert row.order_number is None
                assert row.geo_sid == self.geo_area.sid
                logger.debug("End-dating measure: %s", row.measure_sid)
                yield list(
                    self.measure_ender.end_date_measure(row, self.generating_regulation)
                )

        # Create measures either for the single measure type or a mix
        for (
            matched_old_rows,
            row,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(self.old_rows, self.new_rows):
            for transaction in self.make_new_measure(
                row, matched_old_rows, goods_nomenclature
            ):
                yield transaction

    def make_new_measure(
        self,
        new_row: NewRow,
        matched_old_rows: List[OldMeasureRow],
        goods_nomenclature: GoodsNomenclature,
    ) -> Iterator[List[TrackedModel]]:
        assert new_row is not None
        new_measure_type = self.measure_slicer.get_measure_type(
            matched_old_rows, goods_nomenclature
        )
        footnote_list = [row.footnotes for row in matched_old_rows]
        footnote_ids = list(
            set([footnote for sublist in footnote_list for footnote in sublist])
        )
        footnote_ids.sort()
        footnotes = [
            Footnote.objects.as_at(BREXIT).get(
                footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
            )
            for f in footnote_ids
        ]

        yield list(
            self.measure_creator.create(
                duty_sentence=clean_duty_sentence(new_row.duty_rate),
                geography=self.geo_area,
                goods_nomenclature=goods_nomenclature,
                new_measure_type=new_measure_type,
                authorised_use=False,
                validity_start=BREXIT,
                footnotes=footnotes,
            )
        )


class Command(BaseCommand):
    help = "Imports a Trade Disputes format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "new-spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "old-spreadsheet",
            help="The XLSX file containing existing measures to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--new-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--old-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
            default=200000000,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
            default=200000000,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
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

        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        schedule_sheet_main = new_workbook.sheet_by_name("Main rebalancing measures")
        schedule_sheet_additional = new_workbook.sheet_by_name("Additional rebalancing")
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet1")

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Trade Disputes",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                1,
                counter_generator(options["transaction_id"]),
                counter_generator(start=1),
            ) as env:
                new_rows_main = schedule_sheet_main.get_rows()
                new_rows_additional = schedule_sheet_additional.get_rows()
                old_rows = old_worksheet.get_rows()
                for _ in range(options["new_skip_rows"]):
                    next(new_rows_main)
                    next(new_rows_additional)
                for _ in range(options["old_skip_rows"]):
                    next(old_rows)
                new_rows = list(new_rows_main) + list(new_rows_additional)
                new_rows.sort(key=lambda row: row[col("B")].value)

                importer = TradeDisputesImporter(workbasket, env)
                importer.counters["measure_sid_counter"] = counter_generator(
                    options["measure_sid"]
                )
                importer.counters["measure_condition_sid_counter"] = counter_generator(
                    options["measure_condition_sid"]
                )
                importer.import_sheets(
                    (NewRow(row) for row in new_rows),
                    (OldMeasureRow(row) for row in old_rows),
                )
