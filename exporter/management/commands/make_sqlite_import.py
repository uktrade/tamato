from itertools import chain
from subprocess import run
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Type

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.core.management import BaseCommand
from django.db.models.base import Model
from django.db.models.fields import BooleanField

from common.models.mixins.validity import ValidityMixin


def column_name_to_expr(column: str, model: Type[Model]) -> str:
    try:
        field = model._meta.get_field(column)
        if isinstance(field, BooleanField):
            return f'CASE WHEN \\"{column}\\" IS TRUE THEN 1 ELSE 0 END'
        else:
            return f'\\"{column}\\"'
    except FieldDoesNotExist:
        if column == "validity_start":
            return f'LOWER(\\"{ValidityMixin.valid_between.field.name}\\")'
        elif column == "validity_end":
            return f'UPPER(\\"{ValidityMixin.valid_between.field.name}\\")'
        else:
            raise


def read_sqlite_column_order(filename: str, table: str) -> Iterator[str]:
    cmd = run(
        ["sqlite3", filename, "--cmd", f"PRAGMA table_info({table});"],
        capture_output=True,
        input="",
    )
    for column in cmd.stdout.splitlines():
        name: bytes = column.split(b"|")[1]
        yield name.decode("utf-8")


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        names = (name.split(".")[0] for name in settings.DOMAIN_APPS)
        models = chain(*[apps.get_app_config(name).get_models() for name in names])
        database = settings.DATABASES["default"]

        print(".echo on")
        print(".mode csv")
        for model in models:
            columns = read_sqlite_column_order("cool.db", model._meta.db_table)
            fields = (column_name_to_expr(name, model) for name in columns)
            field_names = ", ".join(fields)

            print(
                ".import '|psql -c \"COPY (SELECT {1} FROM {2}) TO STDOUT (FORMAT csv);\" {0[NAME]}' {2}".format(
                    database,
                    field_names,
                    model._meta.db_table,
                ),
            )

        print("VACUUM;")
        print("PRAGMA optimize;")
