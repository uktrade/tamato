import logging
import sys
from typing import Iterator
from typing import List
from typing import Optional

import django
import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.models import TrackedModel, Transaction
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import clean_duty_sentence, split_groups, parse_duty_parts, \
    convert_eur_to_gbp_tr
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import clean_regulation
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import parse_trade_remedies_duty_expression
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

EUR_GBP_CONVERSION_RATE = 0.83687


class NewRow:
    def __init__(self, new_row: List[Cell]) -> None:
        self.item_id = clean_item_id(new_row[col("A")])
        self.duty_rate = clean_duty_sentence(new_row[col("J")])
        self.maintained = new_row[col("N")].value
        self.regulation_id = clean_regulation(new_row[col("I")])
        self.geo_area = GeographicalArea.objects.as_at(BREXIT).get(
            area_id=new_row[col("K")].value
        )
        self.measure_type = str(int(new_row[col("L")].value))
        self.additional_code = new_row[col("B")].value

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist:
            logger.warning(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            self.goods_nomenclature = None


class TradeRemediesImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {
            "552": MeasureType.objects.get(sid="552"),
            "554": MeasureType.objects.get(sid="554"),
        }
        self.measure_slicer = MeasureTypeSlicer[OldMeasureRow, NewRow](
            get_old_measure_type=lambda r: self.measure_types[r.measure_type],
            get_goods_nomenclature=lambda r: r.goods_nomenclature,
            default_measure_type=MeasureType.objects.get(sid="552"),
        )
        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.new_rows = NomenclatureTreeCollector[NewRow](BREXIT)
        self.row_runner = DualRowRunner(self.old_rows, self.new_rows)
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.generating_regulation = Regulation.current().get(
            regulation_id="C2100005",
            regulation_group=Group.objects.get(group_id="DUM"),
            approved=True,
        )
        if self.first_run:
            #yield self.generating_regulation
            pass
        self.measure_ender = MeasureEndingPattern(
            transaction=self.transaction,
            measure_types=self.measure_types,
        )
        self.measure_creator = MeasureCreatingPatternWithExpression(
            duty_sentence_parser=None,
            generating_regulation=self.generating_regulation,
            transaction=self.transaction,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )
        return []

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
        geo_areas = set()
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
                geo_areas.add(row.geo_sid)
                assert len(geo_areas) == 1, "All geo_areas in buffer need to be same"
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
        if new_row.maintained != "Yes":
            return
        assert matched_old_rows
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

        additional_code_list = list(
            set(
                [
                    row.additional_code_sid
                    for row in matched_old_rows
                    if row.additional_code_sid
                ]
            )
        )
        geo_exclusion_list = [row.excluded_geo_areas for row in matched_old_rows]
        geo_exclusion_ids = list(
            set([geo_exclusion for sublist in geo_exclusion_list for geo_exclusion in sublist])
        )
        geo_exclusion_ids.sort()
        geo_exclusions = [
            GeographicalArea.objects.as_at(BREXIT).get(
                sid=sid
            )
            for sid in geo_exclusion_ids
        ]

        assert (
            len(additional_code_list) <= 1
        )  # no multiple additional codes allowed in same run
        additional_code = (
            AdditionalCode.objects.current().get(sid=additional_code_list[0])
            if additional_code_list
            else None
        )
        # duty_condition_expressions, measure_components = [], []
        # if new_row.duty_rate.startswith("Cond: "):
        #     duty_condition_expressions = parse_trade_remedies_duty_expression(
        #         new_row.duty_rate, eur_gbp_conversion_rate=EUR_GBP_CONVERSION_RATE
        #     )
        # else:
        #     measure_components = parse_trade_remedies_duty_expression(
        #         new_row.duty_rate, eur_gbp_conversion_rate=EUR_GBP_CONVERSION_RATE
        #     )
        duty_condition_parts,  duty_component_parts = \
            matched_old_rows[0].duty_condition_parts, matched_old_rows[0].duty_component_parts

        for row in matched_old_rows:
            assert row.duty_condition_parts == duty_condition_parts
            assert row.duty_component_parts == duty_component_parts

        duty_condition_expressions = parse_duty_parts(
            row.duty_condition_parts,
            EUR_GBP_CONVERSION_RATE,
            conversion=convert_eur_to_gbp_tr
        ) if row.duty_condition_parts else []
        measure_components = parse_duty_parts(
            row.duty_component_parts,
            EUR_GBP_CONVERSION_RATE,
            conversion=convert_eur_to_gbp_tr
        ) if row.duty_component_parts else []

        yield list(
            self.measure_creator.create(
                geography=new_row.geo_area,
                goods_nomenclature=goods_nomenclature,
                new_measure_type=new_measure_type,
                validity_start=BREXIT,
                footnotes=footnotes,
                duty_condition_expressions=duty_condition_expressions,
                measure_components=measure_components,
                additional_code=additional_code,
                geo_exclusion_list=geo_exclusions
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
        )
        parser.add_argument(
            "--old-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
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
        try:
            with django.db.transaction.atomic():
                username = settings.DATA_IMPORT_USERNAME
                try:
                    author = User.objects.get(username=username)
                except User.DoesNotExist:
                    sys.exit(
                        f"Author does not exist, create user '{username}'"
                        " or edit settings.DATA_IMPORT_USERNAME"
                    )

                new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
                new_worksheet = new_workbook.sheet_by_name("Data")
                old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
                old_worksheet = old_workbook.sheet_by_name("Sheet1")

                workbasket, _ = WorkBasket.objects.get_or_create(
                    title=f"Trade Remedies",
                    author=author,
                    status=WorkflowStatus.PUBLISHED,
                )
                transaction, _ = Transaction.objects.get_or_create(workbasket=workbasket, order=1, composite_key='xx')

                with open(options["output"], mode="wb") as output:
                    with EnvelopeSerializer(
                        output,
                        envelope_id=options["envelope_id"],
                        transaction_counter=counter_generator(options["transaction_id"]),
                        message_counter=counter_generator(start=1),
                        max_envelope_size_in_mb=35,
                    ) as env:
                        new_rows = new_worksheet.get_rows()
                        old_rows = old_worksheet.get_rows()
                        for _ in range(options["new_skip_rows"]):
                            next(new_rows)
                        for _ in range(options["old_skip_rows"]):
                            next(old_rows)

                        measure_sid_counter = counter_generator(options["measure_sid"])
                        measure_condition_sid_counter = counter_generator(
                            options["measure_condition_sid"]
                        )

                        # Split by addional code, origin code, measure_type groups
                        new_groups = split_groups(list(new_rows), "A", ["B", "K", "L"])
                        old_groups = split_groups(list(old_rows), "B", ["W", "L", "I"])
                        logger.debug(new_groups.keys())
                        logger.debug(old_groups.keys())

                        group_ids = OrderedSet(
                            list(old_groups.keys()) + list(new_groups.keys())
                        )
                        for i, group_by_id in enumerate(group_ids):
                            new_group_rows = new_groups.get(group_by_id, [])
                            old_group_rows = old_groups.get(group_by_id, [])
                            logger.debug(
                                f"processing group {group_by_id}: {i + 1}/{len(group_ids)} with "
                                f"{len(new_group_rows)} new rows and {len(old_group_rows)} old rows"
                            )
                            importer = TradeRemediesImporter(transaction, env, first_run=i == 0)
                            importer.counters["measure_sid_counter"] = measure_sid_counter
                            importer.counters[
                                "measure_condition_sid_counter"
                            ] = measure_condition_sid_counter
                            importer.import_sheets(
                                (NewRow(row) for row in new_group_rows),
                                (OldMeasureRow(row) for row in old_group_rows),
                            )
        finally:
            django.db.transaction.rollback()
