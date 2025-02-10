"""Miscellaneous utility functions."""

from __future__ import annotations

import json
import os
import re
import typing
from datetime import date
from datetime import datetime
from datetime import timedelta
from functools import lru_cache
from functools import partial
from pathlib import Path
from platform import python_version_tuple
from typing import IO
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

import magic
import wrapt
from defusedxml.common import DTDForbidden
from django.apps import apps
from django.conf import settings
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
from django.http import HttpRequest
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from lxml import etree
from psycopg.types.range import DateRange
from psycopg.types.range import TimestampRange

from common.validators import UpdateType

major, minor, patch = python_version_tuple()


def is_cloud_foundry():
    """Return True if the deployment environment contains a `VCAP_SERVICES` env
    var, indicating a CloudFoundry environment, False otherwise."""
    return "VCAP_SERVICES" in os.environ


def classproperty(fn):
    return classmethod(property(fn))


def database_url_from_env(environment_key: str) -> str:
    """
    Return a database URL string from the environment variable identified by
    `environment_key`. The environment variable should be parsable as a
    JSON-like string and may contain the keys:

        "engine" (Required) - database engine id. For instance "postgres" or "sqlite".
        "username" (Optional if "password" is not present) - database user name.
        "password" (Optional) - database user's password.
        "host" (Optional if "port" is not present) - database hostname.
        "port" (Optional) - database host port.
        "dbname" (Required) - database name.

    If all keys are present, then the returned result would be a string of the
    form:

        <engine>://<username>:<password>@<host>:<port>/<dbname>

    This is a plug-in, less naive version of
    `dbt_copilot_python.database.database_url_from_env()` making `username`,
    `password`, `host` and `port` an optional as described above.
    """
    config = json.loads(os.environ[environment_key])

    username = config.get("username", "")
    password = config.get("password")
    host = config.get("host", "")
    port = config.get("port")

    config["username"] = username
    config["password"] = f":{password}" if username and password else ""
    config["host"] = f"@{host}" if (username or password) and host else host
    config["port"] = f":{port}" if host and port else ""

    return "{engine}://{username}{password}{host}{port}/{dbname}".format(**config)


def is_truthy(value: Union[str, bool]) -> bool:
    """
    Check whether a string represents a True boolean value.

    :param value str: The value to check
    :rtype: bool
    """
    if not value:
        return False

    return str(value).lower() not in ("n", "no", "off", "f", "false", "0")


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


T = TypeVar("T")


def maybe_min(*objs: Optional[T]) -> Optional[T]:
    """Return the lowest out of the passed objects that are not None, or return
    None if all of the passed objects are None."""
    try:
        return min(d for d in objs if d is not None)
    except ValueError:
        return None


def maybe_max(*objs: Optional[T]) -> Optional[T]:
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

    def overlaps(self, compared_date_range: TaricDateRange):
        if self.upper_inf:
            if compared_date_range.upper_inf:
                # will overlap regardless
                return True
            elif compared_date_range.upper >= self.lower:
                return True
        else:
            if compared_date_range.upper_inf:
                if compared_date_range.lower <= self.upper:
                    return True
            else:
                # here nether have inf
                if self.lower <= compared_date_range.lower <= self.upper:
                    # overlap at lower end
                    return True
                elif self.lower <= compared_date_range.upper <= self.upper:
                    # overlap at upper end
                    return True

        return False

    def contains(self, compared_date_range: TaricDateRange):
        """
        Returns a boolean indicating if a taric date range is fully contained
        within a provided date range.

        Args:
            compared_date_range: TaricDateRange to check against

        Returns:
            bool: True if the date range is fully contained within a provided date range, else False.
        """
        lower_contained = self.lower <= compared_date_range.lower
        if compared_date_range.upper_inf:
            if self.upper_inf:
                upper_contained = True
            else:
                upper_contained = False
        else:
            upper_contained = self.upper_inf or self.upper >= compared_date_range.upper

        return lower_contained and upper_contained

    def upper_is_greater(self, compared_date_range: TaricDateRange) -> bool:
        """
        Checks whether this date range ends after the specified date range.

        :param compared_date_range TaricDateRange: The date range to compare
            against
        :rtype: bool
        """
        if self.upper_inf and not compared_date_range.upper_inf:
            return True
        return (
            None not in {self.upper, compared_date_range.upper}
        ) and self.upper > compared_date_range.upper

    @staticmethod
    def merge_ranges(first_range: TaricDateRange, second_range: TaricDateRange):
        result = first_range

        if second_range.overlaps(first_range):
            # get lowest lower
            if second_range.lower < first_range.lower:
                result = TaricDateRange(second_range.lower, first_range.upper)

            # get highest upper
            if first_range.upper is not None:
                if second_range.upper is None:
                    result = TaricDateRange(first_range.lower, None)
                elif second_range.upper > first_range.upper:
                    result = TaricDateRange(first_range.lower, second_range.upper)
        else:
            raise Exception(
                "TaricDateRange Merge not possible for non overlapping ranges",
            )

        return result


# XXX keep for migrations
class TaricDateTimeRange(TimestampRange):
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


RelationPath = Sequence[Tuple[Type[Model], Field]]


@lru_cache
def resolve_path(model: Type[Model], path: str) -> RelationPath:
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
    relation_path: RelationPath = []

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
        assert contained_model is not None

        relation_path.append((contained_model, relation.remote_field))

    return relation_path


def date_ranges_overlap(a: TaricDateRange, b: TaricDateRange) -> bool:
    """Returns true if two date ranges overlap."""
    if a.upper and b.lower > a.upper:
        return False
    if b.upper and a.lower > b.upper:
        return False

    return True


def contained_date_range(
    date_range: TaricDateRange,
    containing_date_range: TaricDateRange,
    fallback: Optional[Any] = None,
) -> Optional[TaricDateRange]:
    """
    Returns a trimmed contained range that is fully contained by the container
    range.

    Trimming is not eager: only the minimum amount of trimming is done to ensure
    that the result is fully contained by the container date range.

    If the two ranges do not overlap, the method returns None.
    """
    a = date_range
    b = containing_date_range

    if not date_ranges_overlap(a, b):
        return fallback

    start_date = None
    end_date = None

    if b.upper:
        if a.upper is None or b.upper < a.upper:
            end_date = b.upper
    if b.lower > a.lower:
        start_date = b.lower

    return TaricDateRange(
        start_date or a.lower,
        end_date or a.upper,
    )


def get_field_tuple(model: Model, field_name: str) -> Tuple[str, Any]:
    """
    Get the value of the named field of the specified model.

    Follows field lookups that span relations, eg:
    "footnote_type__application_code"

    Handles special case for "valid_between__lower".

    :param model django.db.models.Model: The model to fetch the field value from
    :param field str: The name of the field (including relation spanning
        lookups) to fetch
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
    """Provides a decorator and context manager for locking database tables for
    the duration of a decorated function or context block."""

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

    def __init__(self, *models, lock=None):
        if lock is None:
            lock = self.ACCESS_EXCLUSIVE

        if lock not in self.LOCK_TYPES:
            raise ValueError("%s is not a PostgreSQL supported lock mode.")

        self.lock = lock
        self.models = models

    def __enter__(self):
        with atomic():
            with transaction.get_connection().cursor() as cursor:
                for model in self.models:
                    if isinstance(model, str):
                        model = apps.get_model(model)
                    cursor.execute(
                        f"LOCK TABLE {model._meta.db_table} IN {self.lock} MODE",
                    )

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

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

        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            with cls(*models, lock=lock):
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

    These may not be the current versions of each model, e.g. because the
    queryset may be filtered as of a given transaction.

    But if there are two versions of the same tracked model in the queryset,
    only the one with the one with the latest transaction order (which should be
    latest version) is yielded.
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


# This implementation is borrowed from defusedxml's deprecated lxml module https://github.com/tiran/defusedxml/blob/main/defusedxml/lxml.py
def check_docinfo(elementtree, forbid_dtd=False):
    """Check docinfo of an element tree for DTD."""
    docinfo = elementtree.docinfo
    if docinfo.doctype:
        if forbid_dtd:
            raise DTDForbidden(docinfo.doctype, docinfo.system_url, docinfo.public_id)


def parse_xml(source: Union[str, Path, IO], forbid_dtd=True):
    parser = etree.XMLParser(resolve_entities=False)
    elementtree = etree.parse(source, parser)
    check_docinfo(elementtree, forbid_dtd=forbid_dtd)

    return elementtree


def xml_fromstring(text, forbid_dtd=True):
    parser = etree.XMLParser(resolve_entities=False)
    rootelement = etree.fromstring(text, parser)
    elementtree = rootelement.getroottree()
    check_docinfo(elementtree, forbid_dtd=forbid_dtd)

    return rootelement


def get_mime_type(file):
    """Get MIME type of the file by inspecting and infering its type from its
    first 2048 bytes."""

    initial_pos = file.tell()
    file.seek(0)
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(initial_pos)

    return mime_type


def as_date(date_or_datetime: Union[date, datetime]) -> date:
    """Given an object of type datetime.date or datetime.datetime return the
    date portion as type datetime.date."""
    if type(date_or_datetime) is datetime:
        return date_or_datetime.date()
    return date_or_datetime


def format_date_string(date_string: str, short_format=False) -> str:
    """
    Format and return a string representation of a date using the application's
    standard format. If the format of `date_string` could not be parsed, then
    the empty string is returned.

    If the `short_format` parameter is False, then the
    `settings.DATE_FORMAT` is applied, otherwise, the
    `settings.SHORT_DATE_FORMAT` is applied.
    """
    from dateutil import parser as date_parser

    try:
        if short_format:
            return date_parser.parse(date_string).strftime(settings.SHORT_DATE_FORMAT)
        else:
            return date_parser.parse(date_string).strftime(settings.DATE_FORMAT)
    except:
        return ""


def log_timing(logger_function: typing.Callable):
    """
    Decorator function to log start and end times of a decorated function.

    When decorating a function, `logger_function` must be passed in to the
    decorator to ensure the correct logger instance and function are applied.
    `logger_function` may be any one of the logging output functions, but is
    likely to be either `debug` or `info`.
    Example:
        ```
        import logging

        logger = logging.getLogger(__name__)

        @log_timing(logger_function=logger.info)
        def my_function():
            ...
        ```
    """

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        start_time = timezone.localtime()
        logger_function(
            f"Entering the function {wrapped.__name__}() on process "
            f"pid={os.getpid()} at {start_time.isoformat()}",
        )

        result = wrapped(*args, **kwargs)

        end_time = timezone.localtime()
        elapsed_time = end_time - start_time
        logger_function(
            f"Exited the function {wrapped.__name__}() on "
            f"process pid={os.getpid()} at {end_time.isoformat()} after "
            f"an elapsed time of {elapsed_time}.",
        )

        return result

    return wrapper


def make_real_edit(
    tx: "common.models.Transaction",
    cls: Callable,
    obj: Optional["common.models.TrackedModel"],
    data: dict,
    workbasket: "workbasket.models.WorkBasket",
    update_type: UpdateType,
):
    """
    Checks whether an object exists in the workbasket and makes the appropriate
    update/create/delete.

    update_type == CREATE:
    * New model is created in the workbasket

    update_type == UPDATE:
    * nothing in workbasket: New UPDATE version created in workbasket
    * with CREATE/UPDATE in workbasket: Updates the trackedmodel in the workbasket. No new version is created

    update_type == DELETE:
    * nothing in workbasket: New DELETE version created in workbasket
    * with UPDATE in workbasket: Update type of current change in workbasket is changed to DELETE
    * with CREATE in workbasket: Removes the trackedmodel from the workbasket
    """

    data = data or {}

    if update_type == UpdateType.CREATE:
        new_obj = cls(transaction=tx, update_type=update_type, **data)
        new_obj.save()
        return new_obj

    workbasket_objects = workbasket.tracked_models.instance_of(cls)

    if not obj:
        raise ValueError("If update_type is not CREATE obj param is required.")

    if not workbasket_objects.filter(pk=obj.pk).exists():
        # if it's not already in the workbasket, create a new version
        new_version = cls.objects.get(pk=obj.pk).new_version(
            workbasket=workbasket,
            transaction=tx,
            update_type=update_type,
            **data,
        )
        return new_version

    else:
        if update_type == UpdateType.UPDATE:
            cls.objects.filter(pk=obj.pk).update(transaction=tx, **data)
            return cls.objects.get(pk=obj.pk)

        elif update_type == UpdateType.DELETE:
            # we're deleting the object we just created. remove it from the workbasket
            if obj.update_type == UpdateType.CREATE:
                obj.delete()

            # we're now deleting an object instead of updating it. change the update type
            elif obj.update_type == UpdateType.UPDATE:
                cls.objects.filter(pk=obj.pk).update(update_type=UpdateType.DELETE)

        return None


def get_related_names(instance, related_model) -> list[str]:
    """
    Return a list of related names of reverse foreign-key relationships to
    (subclasses of) the specified `related_model` for the given `instance`.

    If a reverse foreign-key relationship exists but no related name has been
    defined, a default name in the format `relatedmodel_set` will be returned.
    If no such relationships exist, an empty list is returned.
    """
    related_names = []
    for field in instance._meta.get_fields():
        if field.one_to_many and issubclass(field.related_model, related_model):
            related_names.append(field.get_accessor_name())
    return related_names


def get_current_view_url(request: HttpRequest) -> str:
    """Returns the resolved URL of the current view."""
    view_name = request.resolver_match.view_name
    args = request.resolver_match.args
    kwargs = request.resolver_match.kwargs
    return reverse(view_name, args=args, kwargs=kwargs)
