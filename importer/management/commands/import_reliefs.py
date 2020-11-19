import logging
import sys
from datetime import datetime
from typing import Iterator
from typing import List

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2._range import DateTimeTZRange

from additional_codes.models import AdditionalCode
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, parse_duty_parts
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import split_groups
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from regulations.validators import RoleType
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

EUR_GBP_CONVERSION_RATE = 0.83687
BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)
MEASURE_TYPES = [
    '117',  '119',
]
NEW_REGULATIONS = [
    'S1812490', 'C2100330'
]
NEW_REGULATION_PARAMS = {
    NEW_REGULATIONS[0]: {
        'regulation_group': 'SUS',
        'published_at': datetime(2018, 11, 29),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Customs (Special Procedures and Outward Processing) (EU Exit) Regulations 2018|'''
            '''S.I. 2018/1249|https://www.legislation.gov.uk/uksi/2018/1249'''
        )
    },
    NEW_REGULATIONS[1]: {
        'regulation_group': 'SUS',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
}
REGULATION_MAPPING_OLD_NEW = {
    'R181517': 'S1812490',
    'R872658': 'C2100330',
}


class NewRow:
    pass


class ReliefsImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        if not self.first_run:
            return []
        self.measure_types = {}
        for measure_type in MEASURE_TYPES:
            self.measure_types[measure_type] = MeasureType.objects.get(sid=measure_type)
        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.generating_regulations = {}
        for i, regulation_id in enumerate(NEW_REGULATIONS):
            params = NEW_REGULATION_PARAMS[regulation_id]
            logger.debug(params['regulation_group'])
            params['regulation_group'] = Group.objects.get(group_id=params['regulation_group'])
            generating_regulation, _ = Regulation.objects.get_or_create(
                regulation_id=regulation_id,
                role_type=RoleType.BASE,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
                **params,
            )
            self.generating_regulations[regulation_id] = generating_regulation
            yield generating_regulation

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )
        self.measure_creator = MeasureCreatingPatternWithExpression(
            duty_sentence_parser=None,
            generating_regulation=None,
            workbasket=self.workbasket,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )

    def handle_row(
        self,
        new_row: None,
        old_row: OldMeasureRow,
    ) -> Iterator[List[TrackedModel]]:
        old_regulation_id_trimmed = old_row.regulation_id[:-1]
        replacement_regulation_id = REGULATION_MAPPING_OLD_NEW.get(old_regulation_id_trimmed, None)
        replacement_regulation = self.generating_regulations[replacement_regulation_id] if replacement_regulation_id else None
        if not replacement_regulation:
            raise ValueError("No replacement regulation found")
        yield list(
            self.measure_ender.end_date_measure(
                old_row=old_row,
                terminating_regulation=replacement_regulation
            )
        )
        yield from self.make_new_measure(old_row, replacement_regulation)

    def make_new_measure(
        self,
        old_row: OldMeasureRow,
        regulation: Regulation,
    ) -> Iterator[List[TrackedModel]]:
        footnotes = [
            Footnote.objects.as_at(BREXIT).get(
                footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
            )
            for f in old_row.footnotes
        ]

        additional_code = None
        if old_row.additional_code_sid:
            additional_code = AdditionalCode.objects.get(
                sid=old_row.additional_code_sid,
            )
        # Parse duty expression
        parsed_duty_condition_expressions = parse_duty_parts(old_row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
            if old_row.duty_condition_parts else []
        parsed_duty_component = parse_duty_parts(old_row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
            if old_row.duty_component_parts else []

        yield list(
            self.measure_creator.create(
                geography=GeographicalArea.objects.as_at(BREXIT).get(
                    sid=old_row.geo_sid,
                ),
                goods_nomenclature=old_row.goods_nomenclature,
                new_measure_type=self.measure_types[old_row.measure_type],
                validity_start=BREXIT,
                footnotes=footnotes,
                duty_condition_expressions=parsed_duty_condition_expressions,
                measure_components=parsed_duty_component,
                additional_code=additional_code,
                generating_regulation=regulation,
            )
        )


class Command(BaseCommand):
    help = "Imports an OGD import/export control format spreadsheet"

    def add_arguments(self, parser):
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
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet1")
        old_rows = old_worksheet.get_rows()
        for _ in range(options["old_skip_rows"]):
            next(old_rows)
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"OGD import and export controls",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=30,
            ) as env:
                importer = ReliefsImporter(
                    workbasket,
                    env,
                )
                importer.counters["measure_sid_counter"] = counter_generator(options["measure_sid"])
                importer.counters[
                    "measure_condition_sid_counter"
                ] = counter_generator(
                    options["measure_condition_sid"]
                )

                old_groups = split_groups(list(old_rows), "B", ["W", "L", "I"])
                logger.debug(old_groups.keys())
                group_ids = OrderedSet(
                    list(old_groups.keys())
                )
                for i, group_by_id in enumerate(group_ids):
                    old_group_rows = old_groups.get(group_by_id, [])
                    logger.debug(str([x[1] for x in old_group_rows]))
                    logger.debug(
                        f"processing group {group_by_id}: {i + 1}/{len(group_ids)} with "
                        f"{len(old_group_rows)} old rows"
                    )
                    importer.import_sheets(
                        (),
                        (OldMeasureRow(row) for row in old_group_rows),
                    )
                    importer.first_run = False
