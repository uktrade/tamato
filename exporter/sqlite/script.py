from pathlib import Path
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union

from django.core.exceptions import FieldDoesNotExist
from django.db.models.base import Model
from django.db.models.expressions import Case
from django.db.models.expressions import Expression
from django.db.models.expressions import F
from django.db.models.expressions import Value
from django.db.models.expressions import When
from django.db.models.fields import BooleanField
from django.db.models.fields import CharField
from django.db.models.fields import DateField
from django.db.models.functions import Lower
from django.db.models.functions import Upper
from django.db.models.query import QuerySet

from common.models.mixins.validity import ValidityMixin


def column_name_to_expr(column: str, model: Type[Model]) -> Union[Expression, F]:
    try:
        field = model._meta.get_field(column)
        if isinstance(field, BooleanField):
            return Case(
                When(**{column: True}, then=Value("1")),
                default=Value("0"),
                output_field=CharField(max_length=1),
            )
        else:
            return F(column)
    except FieldDoesNotExist:
        if column == "validity_start":
            return Lower(
                ValidityMixin.valid_between.field.name,
                output_field=DateField(),
            )
        elif column == "validity_end":
            return Upper(
                ValidityMixin.valid_between.field.name,
                output_field=DateField(),
            )
        else:
            raise


def add_column_to_queryset(column: str, queryset: QuerySet) -> Tuple[QuerySet, str]:
    expr = column_name_to_expr(column, queryset.model)
    if isinstance(expr, Expression):
        column = f"{column}_out" if hasattr(queryset.model, column) else column
        return queryset.annotate(**{column: expr}), column
    else:
        return queryset, column


class ImportScript:
    def __init__(self, directory: Path) -> None:
        self.output_directory = directory

    def add_table(self, model: Type[Model], columns: Sequence[str]):
        queryset = model.objects
        output_columns = []
        for column in columns:
            queryset, output_column = add_column_to_queryset(column, queryset)
            output_columns.append(output_column)

        if hasattr(queryset, "has_approved_state"):
            queryset = queryset.has_approved_state()

        queryset = queryset.values(*output_columns)

        compiler = queryset.query.get_compiler(using=queryset.db)
        sql: bytes = compiler.connection.cursor().mogrify(*compiler.as_sql())

        sql_filename = self.output_directory.joinpath(model._meta.db_table + ".sql")
        with open(sql_filename, mode="wb") as sql_file:
            sql_file.write(b"COPY (")
            sql_file.write(sql)
            sql_file.write(b") TO STDOUT (FORMAT csv);")

        print(
            ".import '|psql -f \"{0}\"' {1}".format(
                str(sql_filename.absolute()),
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
