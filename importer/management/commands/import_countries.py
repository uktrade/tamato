import logging
import sys
from datetime import datetime
from typing import Iterator
from typing import List

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from psycopg2.extras import DateRange
from xlrd.sheet import Cell

from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.validators import AreaCode
from importer.management.commands.patterns import BREXIT
from importer.management.commands.utils import col
from common.serializers import EnvelopeSerializer
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class NewRow:
    def __init__(self, row: List[Cell]) -> None:
        self.ref_id = str(row[col("A")].value)
        self.description = str(row[col("B")].value)
        self.type = {
            "Country": AreaCode.COUNTRY,
            "Territory": AreaCode.REGION,
        }[row[col("C")].value.strip()]
        self.iso2 = str(row[col("E")].value)


class GeoAreaImporter:
    def __init__(self, workbasket: WorkBasket) -> None:
        self.workbasket = workbasket
        max_geo_sid = (
            GeographicalAreaDescription.objects.order_by("sid").reverse()[0].sid
        )
        self.geo_description_counter = counter_generator(max_geo_sid + 1)

    def import_rows(
        self, rows: List[NewRow], start_date: date = BREXIT
    ) -> Iterator[TrackedModel]:
        new_areas = {row.iso2: [row] for row in rows}

        # This dictionary manually specifies a mapping between TARIC3 area IDs
        # and ISO2 codes used in the C&TR. Where there are multiple IDs, the
        # description is made up of a combination in the order listed.
        overrides = {
            "BQ": ["BQ-BO", "BQ-SE", "BQ-SA"],
            "SH": ["SH-HL", "SH-AC", "SH-TA"],
            "XC": ["ES-CE"],
            "XL": ["ES-ML"],
        }

        for key, value in overrides.items():
            existing_data = [new_areas[s][0] for s in value if s in new_areas]
            if existing_data:
                new_areas[key] = existing_data

        for area in GeographicalArea.objects.filter(
            area_code__in=[AreaCode.COUNTRY, AreaCode.REGION]
        ).order_by("area_id"):
            if area.area_id not in new_areas:
                logger.info("No information for area %s – skipped", area.area_id)
                continue

            new_area = new_areas[area.area_id]
            new_types = set(row.type for row in new_area)
            assert (
                len(new_types) == 1
            ), f"New areas specify {new_types} types, should be 1"
            new_type = new_area[0].type

            if area.area_code != new_type:
                yield GeographicalArea(
                    sid=area.sid,
                    area_id=area.area_id,
                    area_code=new_type,
                    parent=area.parent,
                    valid_between=area.valid_between,
                    workbasket=self.workbasket,
                    update_type=UpdateType.UPDATE,
                )

            new_descriptions = [row.description for row in new_area]
            if len(new_descriptions) > 1:
                new_description = " and ".join(
                    [", ".join(new_descriptions[0:-1]), new_descriptions[-1]]
                )
            else:
                new_description = new_descriptions[0]

            description = area.descriptions.as_at(start_date).get()
            if description.description != new_description:
                # TODO: update end date of previous description
                # TODO: assert there are no future description changes
                yield GeographicalAreaDescription(
                    area=area,
                    description=new_description,
                    sid=self.geo_description_counter(),
                    valid_between=DateRange(start_date, None),
                    workbasket=self.workbasket,
                    update_type=UpdateType.CREATE,
                )


class Command(BaseCommand):
    help = "Imports a Country and Territory Register format spreadsheet and updates geographical areas"

    def add_arguments(self, parser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "sheet_name",
            help="The name of the sheet in the XLSX file.",
            type=str,
            default="Sheet1",
        )
        parser.add_argument(
            "--skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
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
                " or edit settings.DATA_IMPORT_USERNAME"
            )

        new_workbook = xlrd.open_workbook(options["spreadsheet"])
        schedule_sheet = new_workbook.sheet_by_name(options["sheet_name"])

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Updates to Geographical area names and types",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                200003,
                counter_generator(options["transaction_id"]),
                counter_generator(start=1),
            ) as env:
                logger.info(f"Importing from %s", schedule_sheet.name)
                new_rows = schedule_sheet.get_rows()
                for _ in range(options["skip_rows"]):
                    next(new_rows)

                geog_importer = GeoAreaImporter(workbasket)
                for model in geog_importer.import_rows(
                    [NewRow(row) for row in new_rows]
                ):
                    env.render_transaction([model])
