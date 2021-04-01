"""Miscellaneous utility functions."""
from __future__ import annotations

from typing import Optional
from typing import TypeVar
from typing import Union

import wrapt
from django.db import transaction
from django.db.transaction import atomic
from psycopg2.extras import DateRange
from psycopg2.extras import DateTimeRange


def is_truthy(value: str) -> bool:
    return str(value).lower() not in ("", "n", "no", "off", "f", "false", "0")


def strint(value: Union[int, str, float]) -> str:
    """
    If the passed value is a number type, return the number as a string with no
    decimal point or places.

    Else just return the string.
    """
    if type(value) in (int, float):
        return str(int(value))
    else:
        return str(value)


def maybe_min(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    """Return the lowest out of the passed objects that are not None, or return
    None if all of the passed objects are None."""
    try:
        return min(d for d in objs if d is not None)
    except ValueError:
        return None


def maybe_max(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    """Return the highest out of the passed objects that are not None, or return
    None if all of the passed objects are None."""
    try:
        return max(d for d in objs if d is not None)
    except ValueError:
        return None


class TaricDateRange(DateRange):
    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)

    def upper_is_greater(self, compared_date_range: TaricDateRange) -> bool:
        if self.upper_inf and not compared_date_range.upper_inf:
            return True
        if (
            None not in {self.upper, compared_date_range.upper}
        ) and self.upper > compared_date_range.upper:
            return True
        return False


# XXX keep for migrations
class TaricDateTimeRange(DateTimeRange):
    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)


def validity_range_contains_range(
    overall_range: DateRange,
    contained_range: DateRange,
) -> bool:
    """
    If the contained_range has both an upper and lower bound, check they are
    both within the overall_range.

    If either end is unbounded in the contained range,it must also be unbounded
    in the overall range.
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


def get_field_tuple(model, field):
    """
    Get the value of the named field of the specified model.

    Handles special case for "valid_between__lower".
    """

    if field == "valid_between__lower":
        return ("valid_between__startswith", model.valid_between.lower)

    if "__" in field:
        child, child_field = field.split("__", 1)
        child_instance = getattr(model, child)
        if not child_instance:
            value = None
        else:
            _, value = get_field_tuple(getattr(model, child), child_field)

    else:
        value = getattr(model, field)

    return field, value


def lock_tables(*models):
    @atomic
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        cursor = transaction.get_connection().cursor()
        for model in models:
            cursor.execute(f"LOCK TABLE {model._meta.db_table}")

        try:
            return wrapped(*args, **kwargs)
        finally:
            cursor.close()

    return wrapper
