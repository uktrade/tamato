import logging
import sys

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange

from common.renderers import counter_generator
from importer.management.commands.patterns import BREXIT, MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)


class Command(BaseCommand):
    help = "Adjust geo areas"

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
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
        )
        parser.add_argument(
            "--group_area_sid",
            help="The SID value to use for the first new group area",
            type=int,
        )
        parser.add_argument(
            "--group_area_description_sid",
            help="The SID value to use for the first new group area description",
            type=int,
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
            title=f"Terminate EU measures",
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
                measure_ender = MeasureEndingPattern(
                    workbasket=workbasket,
                )
                for transaction in self.create_transactions(measure_ender, old_rows):
                    env.render_transaction(transaction)

    def create_transactions(self, measure_ender, old_rows):
        for row in old_rows:
            old_measure_row = OldMeasureRow(row)
            logger.debug(f'Processing regulation: {old_measure_row.regulation_id}')
            yield list(
                measure_ender.end_date_measure(
                    old_row=old_measure_row,
                    terminating_regulation=Regulation.objects.get(
                        regulation_id=old_measure_row.regulation_id,
                        role_type=old_measure_row.regulation_role,
                    )
                )
            )

