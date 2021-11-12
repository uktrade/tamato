from abc import abstractmethod
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from functools import wraps
from itertools import islice
from re import split
from typing import Any
from typing import Sequence
from typing import Union

from openpyxl.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

from common.util import classproperty
from importer.utils import col
from workbaskets.models import WorkBasket

CellValue = Union[date, str, int, None]


def column(label, optional=False, many=False):
    """
    Creates a property that will pass the parsed value from the row to the
    decorated function and caches the result.

    `label` is the alphabetic column index in the spreadsheet.

    If `optional` is True, the column will be skipped if it is empty.

    If `many` is True, the column will be split into multiple values and each
    one will be passed separately to the decorated function.
    """

    def decorate(fn):
        @cached_property
        @wraps(fn)
        def getter(self):
            value = self.row[col(label)].value
            if optional and (value is None or value == ""):
                return None
            elif many:
                if value is None:
                    return []
                value = split("[" + "".join(self.separators) + "]", value)
                return [fn(self, v) for v in value]
            else:
                return fn(self, value)

        setattr(getter, "__col__", col(label))
        return getter

    return decorate


@dataclass
class SheetRowMixin:
    """
    A mixin representing a row model, used for building importers that read data
    from a spreadsheet.

    A row model represents one row on the sheet. Each model should declare a
    number of `column` properties that will be passed each value and should
    convert it to a native result.

    Each importer should also declare a `import_row` method that will be called
    for each row that is found. The method should use the declared column
    attributes as properties to build the final result.

    Each row model should be assumed to be immutable once initialized.
    """

    row: Sequence[Cell]
    separators: Sequence[str] = (",", ";", "|")

    @classproperty
    def columns(cls):
        """A list of column names parsed by this importer in the order specified
        by the `column` decorators."""
        all_columns = []
        for key, value in vars(cls).items():
            if hasattr(value, "__col__"):
                all_columns.append((key, value.__col__))
        return list(k[0] for k in sorted(all_columns, key=lambda k: k[1]))

    @abstractmethod
    def import_row(self, workbasket: WorkBasket) -> Any:
        pass

    @classmethod
    def import_sheet(cls, sheet: Worksheet, workbasket: WorkBasket, *args, **kwargs):
        """Import all of the rows from the passed worksheet, ignoring the first
        (header) row."""
        for row in islice(sheet.iter_rows(), 1, None):
            row_model = cls(row, *args, **kwargs)
            yield row_model.import_row(workbasket)
