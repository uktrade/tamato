# Some measures were accidently deleted when cleaning up EU measures
# This script restores those measures as they were before the clean up

import logging
import sys
from datetime import timedelta
from typing import List

import django
import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature, GoodsNomenclatureIndent, GoodsNomenclatureDescription, \
    GoodsNomenclatureOrigin, GoodsNomenclatureSuccessor
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.import_reliefs import EUR_GBP_CONVERSION_RATE
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression, OldMeasureRow, \
    MeasureEndingPattern, parse_date
from importer.management.commands.utils import EnvelopeSerializer, parse_duty_parts, update_geo_area_description
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)


class CCRow:
    def __init__(self, old_row: List[Cell]) -> None:
        self.goods_nomenclature_sid = str(old_row[1].value)
        self.goods_nomenclature_item_id = str(old_row[2].value)
        self.producline_suffix = str(old_row[3].value)
        self.gn_validity_start_date = parse_date(old_row[4])
        self.gn_validity_end_date = parse_date(old_row[5])
        self.statistical_indicator = int(old_row[6].value)
        self.goods_nomenclature_indent_sid = str(old_row[7].value)
        self.indent_validity_start_date = parse_date(old_row[8])
        self.number_indents = int(old_row[9].value)
        self.description = str(old_row[10].value)
        self.goods_nomenclature_description_period_sid = str(old_row[11].value)
        self.desc_validity_start_date = parse_date(old_row[12])
        self.derived_goods_nomenclature_item_id = str(old_row[13].value)
        self.derived_productline_suffix = str(old_row[14].value)
        self.absorbed_goods_nomenclature_item_id = str(old_row[15].value)
        self.absorbed_productline_suffix = str(old_row[16].value)


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file containing measures to be parsed.",
            type=str,
            default=None,
        )
        parser.add_argument(
            "ticket",
            help="The JIRA ticket ID",
            type=str,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--group_area_sid",
            help="The SID value to use for the first new group area",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--group_area_description_sid",
            help="The SID value to use for the first new group area description",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
            default=1,
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
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Update Measures",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )
        workbook = xlrd.open_workbook(options["spreadsheet"]) if options["spreadsheet"] else None
        mc = MeasureCreatingPatternWithExpression(
            duty_sentence_parser=None,
            generating_regulation=None,
            workbasket=workbasket,
            measure_sid_counter=counter_generator(options["measure_sid"]),
            measure_condition_sid_counter=counter_generator(
                options["measure_condition_sid"]
            )
        )
        me = MeasureEndingPattern(
            workbasket=workbasket,
        )
        counters = {
            "group_area_description_sid_counter": counter_generator(
                options["group_area_description_sid"]
            ),
        }
        transactions = {
            'tops-22': self.create_transactions_tops22,
            'tops-1': self.create_transactions_tops1,
            'tops-12': self.create_transactions_tops12,
        }
        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=30,
            ) as env:
                try:
                    with django.db.transaction.atomic():
                        for ticket in options["ticket"].split(","):
                            if ticket not in transactions:
                                raise ValueError(f'Ticket {ticket} not supported')
                            sheet = workbook.sheet_by_name(ticket) if workbook else None
                            existing_measures = sheet.get_rows() if sheet else None
                            if existing_measures:
                                for _ in range(1):
                                    next(existing_measures)
                            for transaction in transactions[ticket](
                                    mc,
                                    me,
                                    existing_measures,
                                    workbasket,
                                    counters
                            ):
                                for model in transaction:
                                    #model.save()
                                    pass
                                env.render_transaction(transaction)
                finally:
                    django.db.transaction.rollback()

    def process_measure_sheet(self, measure_creator, measure_ender, existing_measures):
        for row in (OldMeasureRow(row) for row in existing_measures):
            if row.measure_sid:
                yield list(
                    measure_ender.end_date_measure(
                        old_row=row,
                        terminating_regulation=Regulation.objects.get(
                            regulation_id=row.regulation_id,
                            role_type=row.regulation_role,
                        )
                    )
                )
            else:
                parsed_duty_condition_expressions = parse_duty_parts(row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
                    if row.duty_condition_parts else []
                parsed_duty_component = parse_duty_parts(row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
                    if row.duty_component_parts else []
                footnote_ids = set(row.footnotes)
                footnotes = []
                for f in footnote_ids:
                    footnotes.append(
                        Footnote.objects.get(
                            footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
                        )
                    )
                excluded_geo_areas = []
                for area in row.excluded_geo_areas:
                    excluded_geo_areas.append(
                        GeographicalArea.objects.as_at(BREXIT).get(
                            sid=area,
                        )
                    )
                yield list(
                    measure_creator.create(
                        geography=GeographicalArea.objects.as_at(BREXIT).get(
                            sid=row.geo_sid,
                        ),
                        goods_nomenclature=row.goods_nomenclature,
                        new_measure_type=MeasureType.objects.get(sid=row.measure_type),
                        geo_exclusion_list=excluded_geo_areas,
                        validity_start=row.measure_start_date,
                        validity_end=row.measure_end_date,
                        footnotes=footnotes,
                        duty_condition_expressions=parsed_duty_condition_expressions,
                        measure_components=parsed_duty_component,
                        additional_code=row.additional_code,
                        generating_regulation=Regulation.objects.get(
                            regulation_id=row.regulation_id,
                            role_type=row.regulation_role,
                            approved=True,
                        ),
                    )
                )

    def create_transactions_tops1(self, measure_creator, measure_ender, existing_measures, workbasket, counters):
        # update GEO areas
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area_sid=217,
            old_area_description_sid=1332,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="GSP – General Framework",
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area_sid=62,
            old_area_description_sid=1333,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="GSP – Least Developed Countries",
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area_sid=51,
            old_area_description_sid=1334,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="GSP – Enhanced Framework",
        ))
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)

    def create_transactions_tops12(self, measure_creator, measure_ender, existing_measures, workbasket, counters):
        for old_row in (OldMeasureRow(row) for row in existing_measures):
            parsed_duty_condition_expressions = parse_duty_parts(old_row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
                if old_row.duty_condition_parts else []
            parsed_duty_component = parse_duty_parts(old_row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
                if old_row.duty_component_parts else []
            footnote_ids = set(old_row.footnotes)
            footnotes = [
                Footnote.objects.as_at(BREXIT).get(
                    footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
                )
                for f in footnote_ids
            ]
            yield list(
                measure_creator.create(
                    geography=GeographicalArea.objects.as_at(BREXIT).get(
                        sid=old_row.geo_sid,
                    ),
                    goods_nomenclature=old_row.goods_nomenclature,
                    new_measure_type=MeasureType.objects.get(sid=old_row.measure_type),
                    validity_start=BREXIT,
                    footnotes=footnotes,
                    duty_condition_expressions=parsed_duty_condition_expressions,
                    measure_components=parsed_duty_component,
                    additional_code=old_row.additional_code,
                    generating_regulation=Regulation.objects.get(
                        regulation_id=old_row.regulation_id,
                        role_type=old_row.regulation_role,
                    ),
                )
            )

    def create_transactions_tops22(self, measure_creator, measure_ender, existing_measures, workbasket, counters):
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)
