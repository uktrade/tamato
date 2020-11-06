import logging
import sys
from datetime import timedelta
from typing import cast
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set

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
        assert new_row is not None
        self.item_id = clean_item_id(new_row[col("C")])
        self.suspension_rate = new_row[col("F")]

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            self.goods_nomenclature = None


class AutonomousSuspensionImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {
            str(m.sid): m
            for m in [
                MeasureType.objects.get(sid="112"),
                MeasureType.objects.get(sid="115"),
            ]
        }
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
            default_measure_type=MeasureType.objects.get(sid="112"),
        )
        self.seasonal_rate_parser = SeasonalRateParser(BREXIT, LONDON)

        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[NewRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)

        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)

        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.suspensions_si, _ = Regulation.objects.get_or_create(
            regulation_id="C2100003",
            regulation_group=Group.objects.get(group_id="SUS"),
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.suspensions_si

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.suspensions_si,
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
        old_sids = cast(Set[int], set())
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
                assert row.geo_sid == self.erga_omnes.sid
                logger.debug("End-dating measure: %s", row.measure_sid)
                yield list(
                    self.measure_ender.end_date_measure(row, self.suspensions_si)
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

        footnote_ids = set(*[r.footnotes for r in matched_old_rows])
        footnotes = [
            Footnote.objects.as_at(BREXIT).get(
                footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
            )
            for f in footnote_ids
        ]

        yield list(
            self.measure_creator.create(
                duty_sentence=clean_duty_sentence(new_row.suspension_rate),
                geography=self.erga_omnes,
                goods_nomenclature=goods_nomenclature,
                new_measure_type=new_measure_type,
                authorised_use=(new_measure_type == self.measure_types["115"]),
                validity_start=BREXIT,
                validity_end=BREXIT.replace(year=2022) - timedelta(days=1),
                footnotes=footnotes,
            )
        )


class Command(BaseCommand):
    help = "Imports a GSP format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "new-spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--new-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "old-spreadsheet",
            help="The XLSX file containing existing measures to be parsed.",
            type=str,
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
        schedule_sheet = new_workbook.sheet_by_name("Suspensions")
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet")

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Autonomous Suspensions",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                200004,
                counter_generator(options["transaction_id"]),
            ) as env:
                logger.info(f"Importing from %s", schedule_sheet.name)
                new_rows = schedule_sheet.get_rows()
                old_rows = old_worksheet.get_rows()
                for _ in range(options["new_skip_rows"]):
                    next(new_rows)
                for _ in range(options["old_skip_rows"]):
                    next(old_rows)

                importer = AutonomousSuspensionImporter(workbasket, env)
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
