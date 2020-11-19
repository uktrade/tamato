# Some measures were accidently deleted when cleaning up EU measures
# This script restores those measures as they were before the clean up

import logging
import sys

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange

from common.renderers import counter_generator
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.import_reliefs import EUR_GBP_CONVERSION_RATE
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression, OldMeasureRow, \
    MeasureEndingPattern
from importer.management.commands.utils import EnvelopeSerializer, parse_duty_parts, update_geo_area_description
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)


class Command(BaseCommand):
    help = ""

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
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
        )
        parser.add_argument(
            "--group_area_description_sid",
            help="The SID value to use for the first new group area description",
            type=int,
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
            title=f"Update GSP",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )
        workbook = xlrd.open_workbook(options["spreadsheet"])
        sheet = workbook.sheet_by_name("gsp_updates")
        existing_measures = sheet.get_rows()
        for _ in range(1):
            next(existing_measures)
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
            )
        }

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=30,
            ) as env:
                for transaction in self.create_transactions(mc, me, existing_measures, workbasket, counters):
                    env.render_transaction(transaction)

    cache = {}
    geo_sid = {
        'India': 154,
    }

    def create_transactions(self, measure_creator, measure_ender, existing_measures, workbasket, counters):
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

        for old_row in (OldMeasureRow(row) for row in existing_measures):
            if old_row.measure_sid:
                if 'reg-' + old_row.regulation_id not in self.cache:
                    self.cache['reg-' + old_row.regulation_id] = Regulation.objects.get(
                        regulation_id=old_row.regulation_id,
                        role_type=old_row.regulation_role,
                    )
                yield list(
                    measure_ender.end_date_measure(
                        old_row=old_row,
                        terminating_regulation=self.cache['reg-' + old_row.regulation_id]
                    )
                )
            else:
                parsed_duty_condition_expressions = parse_duty_parts(old_row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
                    if old_row.duty_condition_parts else []
                parsed_duty_component = parse_duty_parts(old_row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
                    if old_row.duty_component_parts else []
                footnote_ids = set(old_row.footnotes)
                footnotes = []
                for f in footnote_ids:
                    if 'fn-' + f not in self.cache:
                        self.cache['fn-' + f] = Footnote.objects.as_at(BREXIT).get(
                            footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
                        )
                    footnotes.append(self.cache['fn-' + f])
                excluded_geo_areas = []
                for area in old_row.excluded_geo_areas:
                    if 'geo-' + area not in self.cache:
                        self.cache['geo-' + area] = GeographicalArea.objects.as_at(BREXIT).get(
                            sid=self.geo_sid[area],
                        )
                    excluded_geo_areas.append(self.cache['geo-' + area])
                if f'geo-{old_row.geo_sid}' not in self.cache:
                    self.cache[f'geo-{old_row.geo_sid}'] = GeographicalArea.objects.as_at(BREXIT).get(
                        sid=old_row.geo_sid,
                    )
                if 'reg-' + old_row.regulation_id not in self.cache:
                    self.cache['reg-' + old_row.regulation_id] = Regulation.objects.get(
                        regulation_id=old_row.regulation_id,
                        role_type=old_row.regulation_role,
                    )
                if old_row.measure_type not in self.cache:
                    self.cache['mt-' + old_row.measure_type] = MeasureType.objects.get(sid=old_row.measure_type)
                yield list(
                    measure_creator.create(
                        geography=self.cache[f'geo-{old_row.geo_sid}'],
                        goods_nomenclature=old_row.goods_nomenclature,
                        new_measure_type=self.cache['mt-' + old_row.measure_type],
                        geo_exclusion_list=excluded_geo_areas,
                        validity_start=old_row.measure_start_date,
                        validity_end=old_row.measure_end_date,
                        footnotes=footnotes,
                        duty_condition_expressions=parsed_duty_condition_expressions,
                        measure_components=parsed_duty_component,
                        additional_code=old_row.additional_code,
                        generating_regulation=self.cache['reg-' + old_row.regulation_id],
                    )
                )

