"""
Miscellaneous utility functions
"""
from typing import Optional
from typing import TypeVar
from typing import Union

from django.db import connection
from psycopg2.extras import DateRange
from psycopg2.extras import DateTimeRange


def is_truthy(value: str) -> bool:
    return str(value).lower() not in ("", "n", "no", "off", "f", "false", "0")


def strint(value: Union[int, str, float]) -> str:
    """If the passed value is a number type, return the
    number as a string with no deciaml point or places.
    Else just return the string."""
    if type(value) in (int, float):
        return str(int(value))
    else:
        return str(value)


def maybe_min(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    """Return the lowest out of the passed objects that are not None,
    or return None if all of the passed objects are None."""
    try:
        return min(d for d in objs if d is not None)
    except ValueError:
        return None


def maybe_max(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    """Return the highest out of the passed objects that are not None,
    or return None if all of the passed objects are None."""
    try:
        return max(d for d in objs if d is not None)
    except ValueError:
        return None


class TaricDateRange(DateRange):
    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)


# XXX keep for migrations
class TaricDateTimeRange(DateTimeRange):
    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)


def validity_range_contains_range(
    overall_range: DateRange, contained_range: DateRange
) -> bool:
    """
    If the contained_range has both an upper and lower bound, check they are both
    within the overall_range.

    If either end is unbounded in the contained range,it must also be unbounded in the overall range.
    """
    # XXX assumes both ranges are [] (inclusive-lower, inclusive-upper)

    if overall_range.lower_inf and overall_range.upper_inf:
        return True

    if (contained_range.lower_inf and not overall_range.lower_inf) or (
        contained_range.upper_inf and not overall_range.upper_inf
    ):
        return False

    if not overall_range.lower_inf:
        if (
            not contained_range.upper_inf
            and contained_range.upper < overall_range.lower
        ):
            return False

        if contained_range.lower < overall_range.lower:
            return False

    if not overall_range.upper_inf:
        if (
            not contained_range.lower_inf
            and contained_range.lower > overall_range.upper
        ):
            return False

        if contained_range.upper > overall_range.upper:
            return False

    return True


def create_sequence(
    name: str,
    start: Optional[int] = None,
    increment_by: int = 1,
    max_value: Optional[int] = None,
    min_value: Optional[int] = None,
    cache: int = 1,
    cycle: bool = False,
) -> str:
    """Generate SQL to create a PostgreSQL sequence."""

    parts = [
        f"CREATE SEQUENCE IF NOT EXISTS {name}",
        f"INCREMENT BY {increment_by}",
        f"MINVALUE {min_value}" if min_value is not None else "NO MINVALUE",
        f"MAXVALUE {max_value}" if max_value is not None else "NO MAXVALUE",
        f"START {start}" if start is not None else "",
        f"CACHE {cache}",
        "CYCLE" if cycle else "NO CYCLE",
    ]
    return " ".join(parts) + ";"


def get_next_sequence_value(sequence_name: str) -> int:
    """Fetch next value in named sequence."""

    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [sequence_name])
        row = cursor.fetchone()

    return row[0]


def get_field_tuple(model, field):
    """Get the value of the named field of the specified model.
    Handles special case for "valid_between__lower".
    """

    if field == "valid_between__lower":
        return ("valid_between__startswith", model.valid_between.lower)

    if "__" in field:
        child, child_field = field.split("__", 1)
        _, value = get_field_tuple(getattr(model, child), child_field)

    else:
        value = getattr(model, field)

    return field, value
