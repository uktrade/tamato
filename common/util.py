"""Miscellaneous utility functions."""
from __future__ import annotations

from platform import python_version_tuple
from typing import Any
from typing import Optional
from typing import TypeVar
from typing import Union

import wrapt
from django.db import transaction
from django.db.models import F
from django.db.models import Func
from django.db.models import Model
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models.fields import Field
from django.db.models.fields import IntegerField
from django.db.models.functions import Cast
from django.db.transaction import atomic
from psycopg2.extras import DateRange
from psycopg2.extras import DateTimeRange

major, minor, patch = python_version_tuple()

# The preferred style of combining @classmethod and @property is only in 3.9.
# When we stop support for 3.8, we should remove both of these branches.
if int(major) == 3 and int(minor) < 9:
    # https://stackoverflow.com/a/13624858
    class classproperty(object):
        def __init__(self, fget):
            self.fget = fget

        def __get__(self, owner_self, owner_cls):
            return self.fget(owner_cls)


else:

    def classproperty(fn):
        return classmethod(property(fn))


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


class TableLock:
    ACCESS_SHARE = "ACCESS SHARE"
    ROW_SHARE = "ROW SHARE"
    ROW_EXCLUSIVE = "ROW EXCLUSIVE"
    SHARE_UPDATE_EXCLUSIVE = "SHARE UPDATE EXCLUSIVE"
    SHARE = "SHARE"
    SHARE_ROW_EXCLUSIVE = "SHARE ROW EXCLUSIVE"
    EXCLUSIVE = "EXCLUSIVE"
    ACCESS_EXCLUSIVE = "ACCESS EXCLUSIVE"

    LOCK_TYPES = (
        ACCESS_SHARE,
        ROW_SHARE,
        ROW_EXCLUSIVE,
        SHARE_UPDATE_EXCLUSIVE,
        SHARE,
        SHARE_ROW_EXCLUSIVE,
        EXCLUSIVE,
        ACCESS_EXCLUSIVE,
    )

    @classmethod
    def acquire_lock(cls, *models, lock=None):
        """
        Decorator for PostgreSQL's table-level lock functionality.

        Example:
            @transaction.commit_on_success
            @require_lock(MyModel, lock=TableLock.ACCESS_EXCLUSIVE)
            def myview(request)
                ...

        PostgreSQL's LOCK Documentation:
        http://www.postgresql.org/docs/8.3/interactive/sql-lock.html
        """
        if lock is None:
            lock = cls.ACCESS_EXCLUSIVE

        if lock not in cls.LOCK_TYPES:
            raise ValueError("%s is not a PostgreSQL supported lock mode.")

        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            with atomic():
                with transaction.get_connection().cursor() as cursor:
                    for model in models:
                        cursor.execute(f"LOCK TABLE {model._meta.db_table}")

                    return wrapped(*args, **kwargs)

        return wrapper


def get_next_id(queryset: QuerySet[Model], id_field: Field, max_len: int):
    return (
        queryset.annotate(
            next_id=Func(
                Cast(F(id_field.name), IntegerField()) + 1,
                Value(f"FM{'0' * max_len}"),
                function="TO_CHAR",
                output_field=id_field,
            ),
        )
        .exclude(
            next_id__in=queryset.values(id_field.name),
        )
        .order_by(id_field.name)
        .first()
        .next_id
    )


def get_record_code(record: dict[str, Any]) -> str:
    """Returns the concatenated codes for a taric record."""
    return f"{record['record_code']}{record['subrecord_code']}"
