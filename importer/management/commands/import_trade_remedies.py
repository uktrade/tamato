import datetime
import logging
import sys
from collections import OrderedDict
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2.extras import DateRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from certificates.models import CertificateType
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import Expression
from importer.management.commands.utils import MeasureTypeSlicer
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import clean_regulation
from importer.management.commands.utils import col
from importer.management.commands.utils import parse_trade_remedies_duty_expression
from measures.models import DutyExpression
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureConditionComponent
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MeasureType
from measures.models import MonetaryUnit
from quotas.models import QuotaOrderNumber
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
            area_id=new_row[col("K")].value,
        )
        self.measure_type = str(int(new_row[col("L")].value))
        self.additional_code = new_row[col("B")].value

        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id,
                suffix="80",
            )
        except GoodsNomenclature.DoesNotExist:
            logger.warning(
                "Failed to find goods nomenclature %s/%s",
                self.item_id,
                "80",
            )
            self.goods_nomenclature = None


class TRMeasureCreatingPattern(MeasureCreatingPattern):
    def create(
        self,
        goods_nomenclature: GoodsNomenclature,
        geography: GeographicalArea,
        new_measure_type: MeasureType,
        order_number: Optional[QuotaOrderNumber] = None,
        additional_code: AdditionalCode = None,
        validity_start: datetime = None,
        validity_end: datetime = None,
        footnotes: List[Footnote] = [],
        measure_expressions: List[Expression] = [],
    ) -> Iterator[TrackedModel]:
        new_measure = Measure(
            sid=self.measure_sid_counter(),
            measure_type=new_measure_type,
            geographical_area=geography,
            goods_nomenclature=goods_nomenclature,
            valid_between=DateRange(validity_start, validity_end),
            generating_regulation=self.generating_regulation,
            terminating_regulation=(
                self.generating_regulation if validity_end is not None else None
            ),
            order_number=order_number,
            additional_code=additional_code,
            update_type=UpdateType.CREATE,
            workbasket=self.workbasket,
        )
        yield new_measure

        for footnote in self.get_measure_footnotes(new_measure, footnotes):
            yield footnote

        component_sequence_number = 1
        for expression in measure_expressions:
            if expression.condition:
                # Create measure condition
                condition = expression.condition
                measure_condition_code = MeasureConditionCode.objects.get(
                    code=condition.condition_code,
                )
                action = MeasureAction.objects.get(
                    code=condition.action_code,
                )
                if condition.certificate:
                    certificate = Certificate.objects.get(
                        sid=condition.certificate_code,
                        certificate_type=CertificateType.objects.get(
                            sid=condition.certificate_type_code,
                        ),
                    )
                condition = MeasureCondition(
                    sid=self.measure_condition_sid_counter(),
                    dependent_measure=new_measure,
                    component_sequence_number=component_sequence_number,
                    condition_code=measure_condition_code,
                    required_certificate=certificate if condition.certificate else None,
                    action=action,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )
                component_sequence_number += 1
                yield condition

            # Create measure component
            component = expression.component
            duty_expression = DutyExpression.objects.get(
                sid=component.duty_expression_id,
            )
            monetary_unit = None
            if component.monetary_unit_code and component.monetary_unit_code != "%":
                monetary_unit = MonetaryUnit.objects.get(
                    code=component.monetary_unit_code,
                )
            measurement = None
            if component.measurement_unit_code:
                measurement_unit = MeasurementUnit.objects.get(
                    code=component.measurement_unit_code,
                )
                measurement_unit_qualifier = None
                if component.measurement_unit_qualifier_code:
                    measurement_unit_qualifier = MeasurementUnitQualifier.objects.get(
                        code=component.measurement_unit_qualifier_code,
                    )
                measurement = Measurement.objects.get(
                    measurement_unit=measurement_unit,
                    measurement_unit_qualifier=measurement_unit_qualifier,
                )

            if expression.condition:
                yield MeasureConditionComponent(
                    condition=condition,
                    duty_expression=duty_expression,
                    duty_amount=component.duty_amount,
                    monetary_unit=monetary_unit,
                    component_measurement=measurement,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )
            else:
                yield MeasureComponent(
                    duty_expression=duty_expression,
                    duty_amount=component.duty_amount,
                    monetary_unit=monetary_unit,
                    component_measure=new_measure,
                    component_measurement=measurement,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )


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
        self.brexit_to_infinity = DateRange(BREXIT, None)
        self.generating_regulation, _ = Regulation.objects.get_or_create(
            regulation_id="C2100005",
            regulation_group=Group.objects.get(group_id="DUM"),
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        if self.first_run:
            yield self.generating_regulation
        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )
        self.measure_creator = TRMeasureCreatingPattern(
            duty_sentence_parser=None,
            generating_regulation=self.generating_regulation,
            workbasket=self.workbasket,
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
                    self.measure_ender.end_date_measure(
                        row,
                        self.generating_regulation,
                    ),
                )

        # Create measures either for the single measure type or a mix
        for (
            matched_old_rows,
            row,
            goods_nomenclature,
        ) in self.measure_slicer.sliced_new_rows(self.old_rows, self.new_rows):
            for transaction in self.make_new_measure(
                row,
                matched_old_rows,
                goods_nomenclature,
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
        new_measure_type = self.measure_slicer.get_measure_type(
            matched_old_rows,
            goods_nomenclature,
        )
        footnote_list = [row.footnotes for row in matched_old_rows]
        footnote_ids = list(
            set([footnote for sublist in footnote_list for footnote in sublist]),
        )
        footnote_ids.sort()
        footnotes = [
            Footnote.objects.as_at(BREXIT).get(
                footnote_id=f[2:],
                footnote_type__footnote_type_id=f[0:2],
            )
            for f in footnote_ids
        ]

        additional_code_list = list(
            set(
                [
                    row.additional_code_sid
                    for row in matched_old_rows
                    if row.additional_code_sid
                ],
            ),
        )
        assert (
            len(additional_code_list) <= 1
        )  # no multiple additional codes allowed in same run
        additional_code = (
            AdditionalCode.objects.get(sid=additional_code_list[0])
            if additional_code_list
            else None
        )

        parsed_measure_expressions = parse_trade_remedies_duty_expression(
            new_row.duty_rate,
            eur_gbp_conversion_rate=EUR_GBP_CONVERSION_RATE,
        )
        yield list(
            self.measure_creator.create(
                geography=new_row.geo_area,
                goods_nomenclature=goods_nomenclature,
                new_measure_type=new_measure_type,
                validity_start=BREXIT,
                footnotes=footnotes,
                measure_expressions=parsed_measure_expressions,
                additional_code=additional_code,
            ),
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
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--output",
            help="The filename to output to.",
            type=str,
            default="out.xml",
        )

    def handle(self, *args, **options):
        username = settings.DATA_IMPORT_USERNAME
        try:
            author = User.objects.get(username=username)
        except User.DoesNotExist:
            sys.exit(
                f"Author does not exist, create user '{username}'"
                " or edit settings.DATA_IMPORT_USERNAME",
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
                    options["measure_condition_sid"],
                )

                # Split by addional code, origin code, measure_type groups
                new_groups = _split_groups(list(new_rows), "A", ["B", "K", "L"])
                old_groups = _split_groups(list(old_rows), "B", ["W", "L", "I"])
                logger.debug(new_groups.keys())
                logger.debug(old_groups.keys())

                group_ids = OrderedSet(
                    list(old_groups.keys()) + list(new_groups.keys()),
                )
                for i, group_by_id in enumerate(group_ids):
                    new_group_rows = new_groups.get(group_by_id, [])
                    old_group_rows = old_groups.get(group_by_id, [])
                    logger.debug(
                        f"processing group {group_by_id}: {i+1}/{len(group_ids)} with "
                        f"{len(new_group_rows)} new rows and {len(old_group_rows)} old rows",
                    )
                    importer = TradeRemediesImporter(workbasket, env, first_run=i == 0)
                    importer.counters["measure_sid_counter"] = measure_sid_counter
                    importer.counters[
                        "measure_condition_sid_counter"
                    ] = measure_condition_sid_counter
                    importer.import_sheets(
                        (NewRow(row) for row in new_group_rows),
                        (OldMeasureRow(row) for row in old_group_rows),
                    )


def _split_groups(
    rows: List[List[Cell]],
    item_column: str,
    group_by_columns: List[str],
) -> OrderedDict:
    """
    Group rows by group_by_columns and sort ascending on item ID (requirement
    for dual row runner)

    :param rows: all non-empty rows from Excel sheet
    :param item_column: the column where the item ID is found
    :param group_by_columns: list of columns used to group the rows by
    :return: Ordered Dictionary with key group_by_id and value list of rows belonging to the group
    """
    rows.sort(key=lambda row: row[col(item_column)].value)
    groups = OrderedDict()
    for row in rows:
        group_by_values = []
        for column in group_by_columns:
            try:
                value = str(int(row[col(column)].value))
            except ValueError:
                value = str(row[col(column)].value)
            group_by_values.append(value)
        group_by_id = "|".join(group_by_values)
        group_rows = groups.get(group_by_id, [])
        group_rows.append(row)
        groups[group_by_id] = group_rows
    return groups
