import logging
from datetime import datetime
from typing import Union

import django.db
import pytz
import xlrd
from django.apps import apps
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.core.management.base import CommandParser
from xlrd.sheet import Cell

import settings
from common.validators import UpdateType
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MeasureTypeSeries
from workbaskets.models import Transaction
from workbaskets.models import WorkBasket
from workbaskets.models import WorkflowStatus

logger = logging.getLogger(__name__)


def start_date(value: str) -> datetime:
    return pytz.utc.localize(datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))


def end_date(value: str) -> Union[datetime, None]:
    if value == "":
        return None
    else:
        return start_date(value)


PROFILES = {
    ("measures", "DutyExpression"): {
        "sid": int,
        "prefix": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
        "duty_amount_applicability_code": int,
        "measurement_unit_applicability_code": int,
        "monetary_unit_applicability_code": int,
    },
    ("measures", "MonetaryUnit"): {
        "code": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
    },
    ("measures", "MeasurementUnit"): {
        "code": str,
        "abbreviation": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
    },
    ("measures", "MeasurementUnitQualifier"): {
        "code": str,
        "abbreviation": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
    },
    ("measures", "Measurement"): {
        "measurement_unit": lambda v: MeasurementUnit.objects.get(code=v),
        "measurement_unit_qualifier": lambda v: MeasurementUnitQualifier.objects.get(
            code=v
        )
        if v != ""
        else None,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
    },
    ("regulations", "Group"): {
        "group_id": str,
        "description": str,
        "valid_between_lower": start_date,
        "valid_between_upper": lambda v: None,
    },
    ("geo_areas", "GeographicalArea"): {
        "sid": int,
        "area_id": str,
        "area_code": int,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
    },
    ("measures", "MeasureTypeSeries"): {
        "sid": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
        "measure_type_combination": int,
    },
    ("measures", "MeasureType"): {
        "sid": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
        "trade_movement_code": int,
        "priority_code": int,
        "measurement_unit_applicability_code": int,
        "origin_destination_code": int,
        "order_number_capture_code": int,
        "measure_explosion_level": int,
        "description": str,
        "measure_type_series": lambda v: MeasureTypeSeries.objects.get(sid=v),
    },
    ("commodities", "GoodsNomenclature"): {
        "sid": int,
        "item_id": str,
        "suffix": str,
        "valid_between_lower": start_date,
        "valid_between_upper": end_date,
        "statistical": bool,
    },
}


class Command(BaseCommand):
    help = "Imports a single table of reference data from one sheet."

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file to be parsed",
            type=str,
        )
        parser.add_argument(
            "--sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet1",
        )
        parser.add_argument(
            "app",
            help="The name of a Django app containing a model to import into.",
            type=str,
        )
        parser.add_argument(
            "model",
            help="The name of a model to import the data into.",
            type=str,
        )
        parser.add_argument(
            "columns",
            help="The fields in the model corresponding to the columns in the sheet, in order.",
            type=str,
            nargs="+",
        )
        parser.add_argument(
            "--skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--tuples",
            metavar="PREFIX",
            help="The prefix of column names to turn into a tuple. Specify column names using prefix[0], prefix[1]...",
            type=str,
            nargs="+",
        )
        parser.add_argument(
            "--dry-run",
            help="Don't commit the import run",
            action="store_const",
            const=True,
            default=False,
        )

    def handle(self, *args, **options):
        workbook = xlrd.open_workbook(options["spreadsheet"])
        worksheet = workbook.sheet_by_name(options["sheet"])

        config = apps.get_app_config(options["app"])
        ModelClass = config.get_model(options["model"])
        profile = PROFILES[(options["app"], options["model"])]
        logger.info(
            "Importing into model %s from sheet %s", ModelClass.__name__, worksheet
        )

        workbasket_status = WorkflowStatus.PUBLISHED
        username = settings.DATA_IMPORT_USERNAME
        author = User.objects.get(username=username)
        update_type = UpdateType.CREATE

        # Pull out all of the tupes and put them into a dict
        # In alphanumeric order, so that columns will be combined correctly
        keys = options["columns"]
        tuples = {}
        for prefix in options["tuples"]:
            tuples[prefix] = []
            for key in keys:
                if key.startswith(prefix):
                    tuples[prefix].append(key)
            tuples[prefix].sort()

        num_rows = 0
        with django.db.transaction.atomic():
            workbasket, _ = WorkBasket.objects.get_or_create(
                title=f"Data import from spreadsheet",
                author=author,
                status=workbasket_status,
            )

            transaction, _ = Transaction.objects.get_or_create(workbasket=workbasket)

            for pair in enumerate(worksheet.get_rows()):
                num_rows = pair[0]
                row = pair[1]

                if num_rows < options["skip_rows"]:
                    continue

                def cell_to_native(column: str, cell: Cell):
                    return profile[column](cell.value)

                values = map(cell_to_native, keys, row)
                data = dict(zip(keys, values))
                if len(data) < len(keys):
                    raise CommandError(
                        f"Row {num_rows} did not contain enough columns: expected {len(keys)} but got {len(data)}"
                    )

                for prefix, tuplekeys in tuples.items():
                    value = tuple([data[k] for k in tuplekeys])
                    data[prefix] = value
                    for key in tuplekeys:
                        del data[key]

                data["workbasket"] = workbasket
                data["update_type"] = update_type

                instance = ModelClass(**data)
                logger.debug("Create instance %s", instance.__dict__)
                instance.full_clean()
                instance.save()

            if options["dry_run"]:
                raise CommandError("Import aborted before completion.")

        logger.info("Completed import of %d rows", num_rows)
