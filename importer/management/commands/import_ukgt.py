import logging
from functools import cached_property
from typing import cast
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set

from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.import_command import ImportCommand
from importer.management.commands.patterns import add_multiple_row
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import blank
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import spreadsheet_argument
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        assert new_row is not None
        self.additional_code = (
            str(int(new_row[col("C")].value)) if new_row[col("C")].value != "" else None
        )
        self.item_id = clean_item_id(new_row[col("D")])
        self.cet_expression = new_row[col("G")]
        self.duty_expression = new_row[col("H")]
        self.ttr_expression = str(new_row[col("I")].value)
        self.ttr_less_than_ukgt = bool(new_row[col("J")].value)
        self.retained_trade_remedy = bool(new_row[col("K")].value)
        self.injury_margin = bool(new_row[col("L")].value)
        self.footnote_code = blank(new_row[col("P")].value, str)

    @cached_property
    def footnote(self) -> Optional[Footnote]:
        if self.footnote_code:
            return Footnote.objects.as_at(BREXIT).get(
                footnote_type__footnote_type_id=self.footnote_code[0:2],
                footnote_id=self.footnote_code[2:],
            )
        else:
            return None

    @cached_property
    def goods_nomenclature(self) -> Optional[GoodsNomenclature]:
        try:
            return GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning("Failed to find goods nomenclature %s", self.item_id)
            return None


class UKGTImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        third_country_duty = cast(MeasureType, MeasureType.objects.get(sid="103"))
        self.mfn_authorised_use = cast(MeasureType, MeasureType.objects.get(sid="105"))
        self.measure_types = {
            str(m.sid): m for m in [third_country_duty, self.mfn_authorised_use]
        }
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
            default_measure_type=third_country_duty,
        )
        self.measure_ender = MeasureEndingPattern(self.workbasket, self.measure_types)

        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[List[NewRow]](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows, add_new_row=add_multiple_row)

        codes = AdditionalCode.objects.filter(type__sid="2", code__in=["500", "501", "600", "601"])
        self.additional_codes = {
            str(a.type.sid + a.code): a
            for a in codes.all()
        }

        self.erga_omnes = GeographicalArea.objects.as_at(BREXIT).get(area_id="1011")
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.mfn_regulation_group = Group.objects.get(group_id="DNC")

        self.ukgt_si, created = Regulation.objects.get_or_create(
            regulation_id="C2100001",
            defaults={
                "regulation_group": self.mfn_regulation_group,
                "published_at": BREXIT,
                "approved": False,
                "valid_between": self.brexit_to_infinity,
                "workbasket": self.workbasket,
                "update_type": UpdateType.CREATE,
            },
        )
        if created:
            yield self.ukgt_si

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.ukgt_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_id"],
            measure_condition_sid_counter=self.counters["measure_condition_id"],
        )

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
            rows,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(self.old_rows, self.new_rows):
            new_measure_type = self.measure_slicer.get_measure_type(
                matched_old_rows, goods_nomenclature
            )
            for row in rows:
                yield list(
                    self.measure_creator.create(
                        duty_sentence=clean_duty_sentence(
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
                        footnotes=[row.footnote] if row.footnote else [],
                    )
                )


class Command(ImportCommand):
    help = "Imports a UKGT format spreadsheet"
    title = "UK Global Tariff"

    def add_arguments(self, parser):
        spreadsheet_argument(parser, "new")
        parser.add_argument(
            "--new-sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
        )
        spreadsheet_argument(parser, "old")
        parser.add_argument(
            "--old-sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
        )
        id_argument(parser, "measure", 200000000)
        id_argument(parser, "measure-condition", 200000000)
        super().add_arguments(parser)

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer):
        new_rows = self.get_sheet("new", self.options["new_sheet"])
        old_rows = self.get_sheet("old", self.options["old_sheet"])

        importer = UKGTImporter(workbasket, env, counters=self.options["counters"])
        importer.import_sheets(
            (NewRow(row) for row in new_rows),
            (OldMeasureRow(row) for row in old_rows)
            if old_rows
            else iter([None]),
        )
