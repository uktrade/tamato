from typing import Sequence
from typing import Type

from django.core.exceptions import FieldDoesNotExist
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


class ImportScript:
    def add_table(self, model: Type[Model], columns: Sequence[str]):
        fields = (column_name_to_expr(name, model) for name in columns)
        field_names = ", ".join(fields)

        print(
            ".import '|psql -c \"COPY (SELECT {0} FROM {1}) TO STDOUT (FORMAT csv);\"' {1}".format(
                field_names,
                model._meta.db_table,
            ),
        )

    def __enter__(self):
        print(".echo on")
        print(".mode csv")
        return self

    def __exit__(self, *args):
        print("VACUUM;")
        print("PRAGMA optimize;")
