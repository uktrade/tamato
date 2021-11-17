from typing import Any
from typing import Iterable
from typing import Tuple
from typing import Type
from typing import Union

from django.core.exceptions import FieldDoesNotExist
from django.db.models.base import Model
from django.db.models.expressions import Expression
from django.db.models.expressions import F
from django.db.models.fields import CharField
from django.db.models.fields import IntegerField
from django.db.models.fields import TextField
from django.db.models.functions import Cast
from django.db.models.query import QuerySet

from common.models.mixins.validity import ValidityMixin
from common.util import EndDate
from common.util import StartDate


def column_to_expr(column: str, model: Type[Model]) -> Union[Expression, F]:
    """
    Returns the expression necessary to correctly pull a column value out of a
    database table for inclusion in an SQLite schema.

    The column name passed should be the name in the SQLite schema.
    """
    try:
        # Use the column directly if it exists on the model
        field = model._meta.get_field(column)
        if not issubclass(type(field), (CharField, TextField, IntegerField)):
            return Cast(field.name, CharField())
        return F(field.name)
    except FieldDoesNotExist:
        field = ValidityMixin.valid_between.field
        if column == "validity_start":
            return Cast(StartDate(field.name), output_field=CharField())
        elif column == "validity_end":
            return Cast(EndDate(field.name), output_field=CharField())
        else:
            raise


def add_column_to_queryset(column: str, queryset: QuerySet) -> Tuple[QuerySet, str]:
    """
    Return a queryset that contains the data for the passed SQLite column name.

    This will annotate the queryset for any non-material fields and also output
    the column name that will need to be asked for.
    """
    expr = column_to_expr(column, queryset.model)
    if isinstance(expr, Expression):
        column = f"{column}_out" if hasattr(queryset.model, column) else column
        return queryset.annotate(**{column: expr}), column
    else:
        return queryset, column


Operation = Tuple[str, Iterable[Iterable[Any]]]
"""
Structure representing an SQL operation to be run against an SQLite database.

The first value is an SQL string containing placeholder question marks for which
values are to be interpolated. The second value is a list of lists of values to
be used. The operation will be executed once for each list of values in the
second value.

This allows us to define a single operation and pass a queryset as the second
value, and the SQL will be run for every value returned by the queryset.
"""


class Plan:
    """
    A set of operations that can be applied to an SQLite database to import data
    from the attached PostgreSQL database.

    By default, the plan will just set up and finalize the database. Tables
    can be added and the data for them will be queried when the plan is
    executed.

    Once the plan is finished, access the operations using the ``operations``
    property and run them using a :class:`~exporter.sqlite.runner.Runner`.
    """

    def __init__(self) -> None:
        self._operations = []

    @property
    def operations(self) -> Iterable[Operation]:
        return [
            ("PRAGMA locking_mode=EXCLUSIVE", [[]]),
            ("PRAGMA page_size=65536", [[]]),
            ("PRAGMA synchronous=OFF", [[]]),
            ("PRAGMA journal_mode=OFF", [[]]),
            ("BEGIN", [[]]),
            *self._operations,
            ("COMMIT", [[]]),
        ]

    def add_schema(self, sql: str):
        self._operations.append((sql, [[]]))

    def add_data(self, model: Type[Model], columns: Iterable[str]):
        queryset = model.objects
        output_columns = []
        for column in columns:
            queryset, output_column = add_column_to_queryset(column, queryset)
            output_columns.append(output_column)

        if hasattr(queryset, "has_approved_state"):
            queryset = queryset.has_approved_state()

        queryset = queryset.values_list(*output_columns).iterator()
        operation = (
            "INSERT INTO {0} VALUES ({1})".format(
                model._meta.db_table,
                ", ".join(["?"] * len(output_columns)),
            ),
            queryset,
        )
        self._operations.append(operation)
