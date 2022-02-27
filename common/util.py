"""Miscellaneous utility functions."""
from __future__ import annotations

import re
from datetime import timedelta
from functools import lru_cache
from functools import partial
from platform import python_version_tuple
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

import wrapt
from django.db import transaction
from django.db.models import F
from django.db.models import Func
from django.db.models import Model
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Case
from django.db.models.expressions import Expression
from django.db.models.expressions import When
from django.db.models.fields import DateField
from django.db.models.fields import Field
from django.db.models.fields import IntegerField
from django.db.models.fields.related import ForeignObjectRel
from django.db.models.functions import Cast
from django.db.models.functions.text import Lower
from django.db.models.functions.text import Upper
from django.db.transaction import atomic
from django.template import loader
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
    """
    Check whether a string represents a True boolean value.

    :param value str: The value to check
    :rtype: bool
    """
    return str(value).lower() not in ("", "n", "no", "off", "f", "false", "0")


def strint(value: Union[int, str, float]) -> str:
    """
    If the passed value is a number type, return the number as a string with no
    decimal point or places.

    Else just return the string.

    :param value Union[int, str, float]: The value to convert
    :rtype: str
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


def get_accessor(field: Union[Field, ForeignObjectRel]) -> str:
    """Return the attribute name used to access the field on the model."""
    if isinstance(field, ForeignObjectRel):
        return field.get_accessor_name()
    else:
        return field.name


class TaricDateRange(DateRange):
    """DateRange with inclusive bounds by default per TARIC specification."""

    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)

    def upper_is_greater(self, compared_date_range: TaricDateRange) -> bool:
        """
        Checks whether this date range ends after the specified date range.

        :param compared_date_range TaricDateRange: The date range to compare against
        :rtype: bool
        """
        if self.upper_inf and not compared_date_range.upper_inf:
            return True
        return (
            None not in {self.upper, compared_date_range.upper}
        ) and self.upper > compared_date_range.upper


# XXX keep for migrations
class TaricDateTimeRange(DateTimeRange):
    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)


def get_inclusive_date(
    field_name: str,
    extractor: Type[Func],
    add_on_exclusive: int,
) -> Expression:
    """
    Our date ranges are inclusive but Postgres stores them as exclusive on the
    upper bound.

    Hence we sometimes need to subtract a day from the date if we want to get
    inclusive value.
    """
    return Cast(
        extractor(field_name, output_field=DateField())
        - Case(
            When(
                **{f"{field_name}__{extractor.__name__.lower()}_inc": True},
                then=timedelta(days=0),
            ),
            default=timedelta(days=add_on_exclusive),
        ),
        output_field=DateField(),
    )


StartDate = partial(get_inclusive_date, extractor=Lower, add_on_exclusive=-1)
"""SQL expression to extract an inclusive start date from a date range."""

EndDate = partial(get_inclusive_date, extractor=Upper, add_on_exclusive=1)
"""SQL expression to extract an inclusive end date from a date range."""


def validity_range_contains_range(
    overall_range: DateRange,
    contained_range: DateRange,
) -> bool:
    """
    If the contained_range has both an upper and lower bound, check they are
    both within the overall_range.

    If either end is unbounded in the contained range,it must also be unbounded
    in the overall range.

    :param overall_range DateRange: The container date range
    :param contained_range DateRange: The contained date range
    :rtype: bool
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


@lru_cache
def resolve_path(model: Type[Model], path: str):
    """
    Returns an ordered sequence of types and field names of the foreign keys
    representing the passed path, starting with the passed model and following
    relations by name.

    E.g. for a path of 'foo__bar__baz', first the relation 'foo' will be looked
    up and the foreign key on the `Foo` model will be returned, then the
    relation 'bar' will be looked up and the foreign key on the `Bar` model will
    be returned, etc.
    """
    contained_model = model
    relation_path = []

    for step in path.split(LOOKUP_SEP):
        relations = {
            **contained_model._meta.fields_map,
            **contained_model._meta._forward_fields_map,
        }

        if step not in relations:
            raise ValueError(
                f"{step!r} is not a valid relation for {contained_model!r}. "
                f"Choices are: {relations.keys()!r}",
            )

        relation = relations[step]
        contained_model = relation.related_model
        relation_path.append((contained_model, relation.remote_field))

    return relation_path


def get_field_tuple(
    model: Model,
    field_name: str,
    default: Any = None,
) -> Tuple[str, Any]:
    """
    Get the value of the named field of the specified model.

    Follows field lookups that span relations, eg: "footnote_type__application_code"

    Handles special case for "valid_between__lower".

    :param model django.db.models.Model: The model to fetch the field value from
    :param field str: The name of the field (including relation spanning lookups) to fetch
    :rtype: Any
    """

    if field_name == "valid_between__lower":
        return "valid_between__startswith", model.valid_between.lower

    if "__" in field_name:
        related, related_field_name = field_name.split("__", 1)
        related_model = getattr(model, related)
        if not related_model:
            value = None
        else:
            _, value = get_field_tuple(related_model, related_field_name)

    else:
        value = getattr(model, field_name)

    return field_name, value


class TableLock:
    """Provides a decorator for locking database tables for the duration of a
    decorated function."""

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


def get_next_id(queryset: QuerySet, id_field: Field, max_len: int):
    """
    Fetch the next sequential ID value by incrementing the maximum ID value in a
    queryset.

    :param queryset QuerySet: The queryset to get the next sequential ID from
    :param id_field Field: The ID field to consider
    :param max_len int: The maximum length of an ID value
    """
    if not queryset:
        return "1".zfill(max_len)

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


def get_record_code(record: Dict[str, Any]) -> str:
    """Returns the concatenated codes for a taric record."""
    return f"{record['record_code']}{record['subrecord_code']}"


CAMEL_CASE_CAPS = re.compile(r"(?!^)([A-Z]+)")


def get_taric_template(model) -> str:
    """
    Convert TrackedModel class names to snake_case.

    Doesn't need to handle anything beyond WordsLikeThis.
    """

    snake_case_name = CAMEL_CASE_CAPS.sub(r"_\1", model.__class__.__name__).lower()
    template_name = f"taric/{snake_case_name}.xml"

    try:
        loader.get_template(template_name)
    except loader.TemplateDoesNotExist as e:
        raise loader.TemplateDoesNotExist(
            f"Taric template {template_name} not found. All TrackedModel "
            "subclasses must either have a taric template with a name matching the "
            'class at "taric/{class_name}.xml" or override the get_taric_template '
            "method, returning an existing template.",
        ) from e

    return template_name


def get_model_indefinite_article(model_instance: Model) -> Optional[str]:
    """Returns "a" or "an" based on the verbose_name."""

    # XXX naive, but works for all current models
    name = model_instance._meta.verbose_name

    # verbose_name is initialized to None, so typing thinks it is Optional
    if name:
        return "an" if name[0] in ["a", "e", "i", "o", "u"] else "a"


def get_latest_versions(qs):
    """
    Yields only the latest versions of each model within the provided queryset.

    These may not be the current versions of each model,
    e.g. because the queryset may be filtered as of a given transaction.

    But if there are two versions of the same tracked model in the queryset,
    only the one with the one with the latest transaction order
    (which should be latest version) is yielded.
    """
    keys = set()

    for model in qs.order_by(
        "-transaction__partition",
        "-transaction__order",
    ):
        key = tuple(model.get_identifying_fields().values())
        if key not in keys:
            keys.add(key)
            yield model
