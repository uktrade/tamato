import logging
import re
import sys
from datetime import date
from datetime import datetime
from datetime import timedelta
from itertools import islice
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Type

import django.db
import pytz
import xlrd
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields.ranges import DateTimeRangeField
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.core.management.base import CommandParser
from django.db.models.fields import BooleanField
from django.db.models.fields import CharField
from django.db.models.fields import DateField
from django.db.models.fields import Field
from django.db.models.fields import IntegerField
from django.db.models.fields import TextField
from django.db.models.fields.related import ForeignKey
from xlrd.sheet import Cell

from common.models import ShortDescription
from common.models import TrackedModel
from common.validators import UpdateType
from importer.management.commands.patterns import parse_date
from workbaskets.models import WorkBasket
from workbaskets.models import WorkflowStatus

logger = logging.getLogger(__name__)

COLUMN_NAME = re.compile(r"(\w+)(?:\[(\d+)\])?")


Transformer = Callable[[Cell], Any]
Setter = Callable[[Dict, Any], None]


def to_datetime(value: str) -> datetime:
    return pytz.utc.localize(datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))


def to_date(value: str) -> date:
    return pytz.utc.localize(datetime.strptime(value, "%Y-%m-%d")).date()


def blank(blank: bool, transformer: Transformer) -> Transformer:
    def transform(value: Any) -> Any:
        if blank and value == "":
            return None
        else:
            return transformer(value)

    return transform


def val(t: Transformer) -> Transformer:
    return lambda cell: t(cell.value)


def get_type_transformer(
    field: Optional[Field], index: Optional[int] = None
) -> Transformer:
    if field is None:
        return null_transformer

    if issubclass(type(field), ShortDescription):
        return val(str)
    if issubclass(type(field), (CharField, TextField)):
        return blank(field.blank, val(str))
    if issubclass(type(field), IntegerField):
        return blank(field.blank, val(int))
    if issubclass(type(field), BooleanField):
        return blank(field.blank, val(bool))
    if issubclass(type(field), DateTimeRangeField):
        return blank(True, parse_date)
    if issubclass(type(field), DateField):
        return blank(field.blank, lambda c: parse_date(c).date())
    if issubclass(type(field), ForeignKey):
        related_model = field.related_model
        id_field_name = related_model.identifying_fields[index or 0]
        id_field = related_model._meta.get_field(id_field_name)
        num_values = len(related_model.identifying_fields)
        transformer = get_type_transformer(id_field)
        if num_values == 1:

            def transform(value: Cell) -> Any:
                return related_model.objects.get(**{id_field_name: transformer(value)})

            return blank(field.blank, transform)
        else:
            return blank(field.blank, transformer)

    raise CommandError(f"Don't know how to transform {field} of type {type(field)}")


def get_type_setter(field: Optional[Field], index: Optional[int]) -> Setter:
    if field is None:
        return null_setter

    def default_setter(data: Dict, value: Any):
        data[field.name] = value

    if type(field) is DateTimeRangeField:
        assert index is not None
        assert int(index) < 2 and int(index) >= 0

        def setter(data: Dict, value: Any):
            if field.name not in data:
                data[field.name] = [None, None]
            if index == 1 and value:
                value += timedelta(days=1)
            data[field.name][index] = value

        return setter
    elif type(field) is ForeignKey:
        related_model = field.related_model
        id_field_name = related_model.identifying_fields[index or 0]
        num_values = len(related_model.identifying_fields)

        if num_values <= 1:
            return default_setter
        else:

            def setter(data: Dict, value: Any):
                if field.name not in data:
                    data[field.name] = {}
                data[field.name][id_field_name] = value
                assert len(data[field.name].keys()) <= num_values
                if len(data[field.name].keys()) == num_values:
                    data[field.name] = related_model.objects.get(**data[field.name])

            return setter
    else:
        return default_setter


null_transformer: Transformer = lambda v: None
null_setter: Setter = lambda d, v: None


class SheetImporter:
    def __init__(
        self, model_class: Type, workbasket: WorkBasket, *columns: Optional[str]
    ) -> None:
        self.model_class = model_class
        self.workbasket = workbasket

        # Pull out all of the tupes and put them into a dict
        # In alphanumeric order, so that columns will be combined correctly
        matches = [
            (COLUMN_NAME.search(name).groups() if name else (None, None))
            for name in columns
        ]
        names = [match[0] for match in matches]
        indexes = [
            (int(match[1]) if match[1] is not None else None) for match in matches
        ]
        fields = [
            (self.model_class._meta.get_field(name) if name else None) for name in names
        ]
        self.transformers = [
            get_type_transformer(field, index) for field, index in zip(fields, indexes)
        ]
        self.setters = [
            get_type_setter(field, index) for field, index in zip(fields, indexes)
        ]

    def import_rows(self, rows: Iterable[List[Cell]]) -> Iterator[TrackedModel]:
        for row in rows:
            assert len(row) >= len(self.setters)

            data = dict()
            for transformer, setter, value in zip(self.transformers, self.setters, row):
                setter(data, transformer(value))

            data["workbasket"] = self.workbasket
            data["update_type"] = UpdateType.CREATE

            instance = self.model_class(**data)
            logger.debug("Create instance %s", instance.__dict__)
            yield instance


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
        logger.info(
            "Importing into model %s from sheet %s", ModelClass.__name__, worksheet.name
        )

        workbasket_status = WorkflowStatus.PUBLISHED
        username = settings.DATA_IMPORT_USERNAME
        try:
            author = User.objects.get(username=username)
        except User.DoesNotExist:
            sys.exit(
                f"Author does not exist, create user '{username}'"
                " or edit settings.DATA_IMPORT_USERNAME"
            )

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Data import from spreadsheet of {ModelClass.__name__}",
            author=author,
            status=workbasket_status,
        )

        importer = SheetImporter(ModelClass, workbasket, options["columns"])

        num_rows = 0
        with django.db.transaction.atomic():
            rows = islice(worksheet.get_rows(), options["skip_rows"], None)
            for instance in importer.import_rows(rows):
                num_rows += 1
                try:
                    instance.save()
                except ValidationError as ex:
                    logger.error("Validation error creating %s", instance.__dict__)
                    raise ex

            if options["dry_run"]:
                logger.info("Rolling back transaction...")
                raise django.db.transaction.set_rollback(True)

        logger.info("Completed import of %d rows", num_rows)
