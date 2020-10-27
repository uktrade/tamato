import logging
import sys
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import cast

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import col
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        assert new_row is not None
        self.additional_code = (
            str(int(new_row[col("C")].value)) if new_row[col("C")].value != "" else None
        )
        self.commodity_code = str(new_row[col("D")].value)
        self.cet_expression = new_row[col("G")]
        self.duty_expression = new_row[col("H")]
        self.ttr_expression = str(new_row[col("I")].value)
        self.ttr_less_than_ukgt = bool(new_row[col("J")].value)
        self.retained_trade_remedy = bool(new_row[col("K")].value)
        self.injury_margin = bool(new_row[col("L")].value)

        if len(self.commodity_code) == 8:
            self.item_id = self.commodity_code + "00"
        else:
            self.item_id = self.commodity_code

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning("Failed to find goods nomenclature %s", self.item_id)
            self.goods_nomenclature = None


class UKGTImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        third_country_duty = cast(MeasureType, MeasureType.objects.get(sid="103"))
        self.mfn_authorised_use = cast(MeasureType, MeasureType.objects.get(sid="105"))
        self.measure_types = {
            int(m.sid): m for m in [third_country_duty, self.mfn_authorised_use]
        }
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
        )
        self.measure_ender = MeasureEndingPattern(self.workbasket, self.measure_types)

        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[NewRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)

        pharma_additional_code = cast(
            AdditionalCode, AdditionalCode.objects.get(type__sid="2", code="500")
        )
        other_additional_code = cast(
            AdditionalCode, AdditionalCode.objects.get(type__sid="2", code="501")
        )
        self.additional_codes = {
            str(a.type.sid + a.code): a
            for a in [pharma_additional_code, other_additional_code]
        }

        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.mfn_regulation_group = Group.objects.get(group_id="DNC")

        self.ukgt_si, _ = Regulation.objects.get_or_create(
            regulation_id="C2100001",
            regulation_group=self.mfn_regulation_group,
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.ukgt_si

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.ukgt_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )

    def clean_duty_sentence(self, cell: Cell) -> str:
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            # This is a percentage value that Excel has
            # represented as a number.
            return f"{cell.value * 100}%"
        else:
            # All other values will apear as text.
            return cell.value

    def select_rate_on_trade_remedy(self, row: NewRow) -> Cell:
        """Where an injury margin applies the CET rate should
        be retained until the TRs have been reviewed."""
        if row.injury_margin:
            return row.cet_expression
        else:
            return row.duty_expression

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
            # End date all the old rows in either case
            # We must do this first to maintain ME32
            for row in rows:
                assert (
                    row.measure_sid not in old_sids
                ), f"Measure appears more than once: {row.measure_sid}"
                old_sids.add(row.measure_sid)

                assert row.geo_sid == self.erga_omnes.sid
                assert row.order_number is None
                yield list(self.measure_ender.end_date_measure(row, self.ukgt_si))

        # Create measures either for the single measure type or a mix
        for (
            matched_old_rows,
            row,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(self.old_rows, self.new_rows):
            new_measure_type = self.measure_slicer.get_measure_type(
                matched_old_rows, goods_nomenclature
            )
            for transaction in self.measure_creator.create(
                duty_sentence=self.clean_duty_sentence(
                    self.select_rate_on_trade_remedy(row)
                ),
                goods_nomenclature=goods_nomenclature,
                geography=self.erga_omnes,
                new_measure_type=new_measure_type,
                authorised_use=(new_measure_type == self.mfn_authorised_use),
                validity_start=BREXIT,
                additional_code=(
                    self.additional_codes[row.additional_code]
                    if row.additional_code
                    else None
                ),
            ):
                yield transaction


class Command(BaseCommand):
    help = "Imports a UKGT format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "new-spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--new-sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
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
            "--old-sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
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
        new_worksheet = new_workbook.sheet_by_name(options["new_sheet"])
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name(options["old_sheet"])

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"UK Global Tariff",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                200001,
                counter_generator(options["transaction_id"]),
            ) as env:

                logger.info(f"Importing from %s", new_worksheet.name)
                new_rows = new_worksheet.get_rows()
                old_rows = old_worksheet.get_rows()
                for _ in range(options["new_skip_rows"]):
                    next(new_rows)
                for _ in range(options["old_skip_rows"]):
                    next(old_rows)

                importer = UKGTImporter(workbasket, env)
                importer.counters["measure_sid_counter"] = counter_generator(
                    options["measure_sid"]
                )
                importer.counters["measure_condition_sid_counter"] = counter_generator(
                    options["measure_sid"]
                )

                importer.import_sheets(
                    (NewRow(row) for row in new_rows),
                    (OldMeasureRow(row) for row in old_rows),
                )
