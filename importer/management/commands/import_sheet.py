import logging
import re
from datetime import date
from datetime import datetime
from distutils.util import strtobool
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Type

import pytz
import xlrd
from django.apps import apps
from django.contrib.postgres.fields.ranges import DateTimeRangeField
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.core.management.base import CommandParser
from django.db.models.fields import BooleanField
from django.db.models.fields import CharField
from django.db.models.fields import DateField
from django.db.models.fields import DecimalField
from django.db.models.fields import Field
from django.db.models.fields import IntegerField
from django.db.models.fields import TextField
from django.db.models.fields.related import ForeignKey
from xlrd.sheet import Cell

from common.models import ShortDescription
from common.models import TrackedModel
from common.validators import UpdateType
from importer.management.commands.import_command import ImportCommand
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import spreadsheet_argument
from importer.management.commands.utils import strint
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

COLUMN_NAME = re.compile(r"(\w+)(?:\[(\d+)\])?")


Transformer = Callable[[Cell], Any]
Setter = Callable[[Dict, Any], None]


def to_datetime(value: str) -> datetime:
    return pytz.utc.localize(datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))


def to_date(value: str) -> date:
    return pytz.utc.localize(datetime.strptime(value, "%Y-%m-%d")).date()


def parse_date(cell: Cell) -> datetime:
    if cell.ctype == xlrd.XL_CELL_DATE:
        return pytz.utc.localize(xlrd.xldate.xldate_as_datetime(cell.value, datemode=0))
    else:
        return pytz.utc.localize(datetime.strptime(cell.value, r"%Y-%m-%d"))


def blank(blank: bool, transformer: Transformer) -> Transformer:
    def transform(cell: Cell) -> Any:
        if blank and cell.value == "":
            return None
        else:
            return transformer(cell)

    return transform


def val(t: Callable[[Any], Any]) -> Transformer:
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
        return blank(field.blank, strint)
    if issubclass(type(field), DecimalField):
        return blank(field.blank, lambda cell: str(cell.value))
    if issubclass(type(field), BooleanField):
        return blank(field.blank, val(strtobool))
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
                data = {id_field_name: transformer(value)}
                logger.debug("Looking up %s using values %s", related_model, data)
                return related_model.objects.get(**data)

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


class Command(ImportCommand):
    help = "Imports a single table of reference data from one sheet."
    title = "Data import from spreadsheet"

    def add_arguments(self, parser: CommandParser):
        spreadsheet_argument(parser, "import")
        parser.add_argument(
            "--sheet",
            help="The sheet name in the XLSX containing the data",
            type=str,
            default="Sheet",
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
        super().add_arguments(parser)

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer) -> None:
        config = apps.get_app_config(self.options["app"])
        ModelClass = config.get_model(self.options["model"])
        logger.info(
            "Importing into model %s from sheet %s",
            ModelClass.__name__,
            self.options["sheet"],
        )

        importer = SheetImporter(ModelClass, workbasket, *self.options["columns"])

        num_rows = 0
        rows = self.get_sheet("import", self.options["sheet"])
        for instance in importer.import_rows(rows):
            num_rows += 1
            try:
                instance.save()
                env.render_transaction([instance])
            except ValidationError as ex:
                logger.error("Validation error creating %s", instance.__dict__)
                raise ex

        logger.info("Completed import of %d rows", num_rows)
