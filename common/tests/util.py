import contextlib
import importlib
from datetime import date
from datetime import datetime
from datetime import timezone
from functools import lru_cache
from functools import wraps
from io import BytesIO
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Type
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.db.models.base import ModelBase
from django.template.loader import render_to_string
from django.urls import get_resolver
from django.urls import reverse
from django_filters.views import FilterView
from freezegun import freeze_time
from lxml import etree

from common.business_rules import BusinessRule
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.renderers import counter_generator
from common.serializers import validate_taric_xml_record_order
from common.tests import factories
from common.util import TaricDateRange
from common.util import get_accessor
from common.util import get_field_tuple

INTERDEPENDENT_IMPORT_IMPLEMENTED = True
UPDATE_IMPORTER_IMPLEMENTED = True
EXPORT_REFUND_NOMENCLATURE_IMPLEMENTED = False
COMMODITIES_IMPLEMENTED = True
MEURSING_TABLES_IMPLEMENTED = False
PARTIAL_TEMPORARY_STOP_IMPLEMENTED = False
UTC = timezone.utc

requires_commodities = pytest.mark.skipif(
    not COMMODITIES_IMPLEMENTED,
    reason="Commodities not implemented",
)

requires_export_refund_nomenclature = pytest.mark.skipif(
    not EXPORT_REFUND_NOMENCLATURE_IMPLEMENTED,
    reason="Export refund nomenclature not implemented",
)

requires_meursing_tables = pytest.mark.skipif(
    not MEURSING_TABLES_IMPLEMENTED,
    reason="Meursing tables not implemented",
)

requires_partial_temporary_stop = pytest.mark.skipif(
    not PARTIAL_TEMPORARY_STOP_IMPLEMENTED,
    reason="Partial temporary stop not implemented",
)

requires_interdependent_import = pytest.mark.skipif(
    not INTERDEPENDENT_IMPORT_IMPLEMENTED,
    reason="Interdependent imports not implemented",
)

requires_update_importer = pytest.mark.skipif(
    not UPDATE_IMPORTER_IMPLEMENTED,
    reason="Requires Updating importers to be implemented",
)


@contextlib.contextmanager
def raises_if(exception, expected, *args, **kwargs):
    if expected:
        yield from pytest.raises(exception, *args, **kwargs)
    else:
        yield


@contextlib.contextmanager
def add_business_rules(
    model: Type[TrackedModel], *rules: Type[BusinessRule], indirect=False
):
    """Attach BusinessRules to a TrackedModel."""
    target = f"{'indirect_' if indirect else ''}business_rules"
    rules = (*rules, *getattr(model, target, []))
    with patch.object(model, target, new=tuple(rules)):
        yield model


class TestRule1(BusinessRule):
    __test__ = False
    validate = MagicMock()


class TestRule2(BusinessRule):
    __test__ = False
    validate = MagicMock()


def check_validator(validate, value, expected_valid):
    try:
        validate(value)
    except ValidationError:
        if expected_valid:
            pytest.fail(f'Unexpected validation error for value "{value}"')
    except Exception:
        raise
    else:
        if not expected_valid:
            pytest.fail(f'Expected validation error for value "{value}"')


def make_duplicate_record(factory, identifying_fields=None):
    """Creates two records using the passed factory that are duplicates of each
    other and returns the record created last."""
    existing = factory.create()

    # allow overriding identifying_fields
    if identifying_fields is None:
        identifying_fields = list(factory._meta.model.identifying_fields)

    return factory.create(
        **dict(get_field_tuple(existing, field) for field in identifying_fields)
    )


def make_non_duplicate_record(factory, identifying_fields=None):
    """Creates two records using the passed factory that are not duplicates of
    each other and returns the record created last."""
    existing = factory.create()
    not_duplicate = factory.create()

    if identifying_fields is None:
        identifying_fields = list(factory._meta.model.identifying_fields)

    assert any(
        get_field_tuple(existing, f) != get_field_tuple(not_duplicate, f)
        for f in identifying_fields
    )

    return not_duplicate


def get_checkable_data(model: TrackedModel, ignore=frozenset()):
    """
    Returns a dict representing the model's data ignoring any automatically set
    fields and fields with names passed to `ignore`.

    The returned data will contain the identifying fields for any linked
    models rather than internal PKs.

    For example:

        get_checkable_data(FootnoteDescriptionFactory(), ignore={"sid"})
        # {
        #   "description": "My sample footnote text",
        #   "described_footnote": {
        #     "footnote_type__footnote_type_id": "FN"
        #     "footnote_id": "123",
        #    },
        # }
    """
    checked_field_names = {f.name for f in model.copyable_fields} - set(ignore)
    data = {
        name: getattr(model, get_accessor(model._meta.get_field(name)))
        for name in checked_field_names
    }
    identifying_fields = {
        name: data[name].get_identifying_fields()
        for name in checked_field_names
        if hasattr(data[name], "identifying_fields")
    }
    data.update(identifying_fields)
    return data


def fully_qualified_classname(cls):
    return f"{cls.__module__}.{cls.__qualname__}"


def get_class_based_view_urls(prefix=lambda **kwargs: True):
    """
    Iterator over all class based views, and url patterns. Users may filter on
    view or url_pattern, by providing a prefix function.

    yields view, url_pattern

    url_pattern is a tuple (bits, p_pattern, default_args, pattern_converters)
    the format is decided by djangos resolver.reverse_dict, for more info
    see the implementation there.

    Class based views are de-duped, so only the first combination of view, params
    if yielded.

    def prefix(**kwargs):
        view = kwargs["view"]
        url_pattern = kwargs["url_pattern"]
        # Filter by view or pattern here, e.g. on view.view_class
        return True

    >>> get_class_based_view_urls(prefix=prefix)
    """
    resolver = get_resolver()

    views = set()
    for view, url_pattern in resolver.reverse_dict.items():
        # url_pattern is a tuple of:
        #   (bits, p_pattern, default_args, pattern_converters)
        #   See: django resolver.reverse_dict implementation
        view_class = getattr(view, "view_class", None)
        if view_class is None:
            # Skip function based views.
            continue

        if prefix(view=view, url_pattern=url_pattern):
            bits = url_pattern[0]
            url_params = bits[0][1]
            views_key = (fully_qualified_classname(view_class), tuple(url_params))
            if views_key not in views:
                views.add(views_key)
                yield view, url_pattern


def view_is_subclass(desired_view_class):
    """
    Return a Prefix function for get_class_based_views that allows filtering by
    a subclass of a class based view.

    >>> get_class_based_view_urls(prefix=view_is_subclass(TrackedModelDetailMixin))
    """

    def prefix(view=None, **kwargs):
        return issubclass(view.view_class, desired_view_class)

    return prefix


def view_url_pattern_starts_with(url_start):
    """Return a Prefix function for get_class_based_views that filtering views,
    only returning those who's url_pattern starts with some string."""

    def prefix(url_pattern=None, **kwargs):
        # url_pattern is a tuple of:
        #   (bits, p_pattern, default_args, pattern_converters)
        #   See: django resolver.reverse_dict implementation
        bits = url_pattern[0]
        return bits[0][0].startswith(url_start)

    return prefix


def get_class_based_view_urls_matching_url(
    url_start,
    prefix=lambda **kwargs: True,
    assert_contains_view_classes=None,
):
    """
    Return a list of tuples of (view, url pattern), where url_pattern starts
    with the supplied string.

    Users may pass optionally assert_contains_view_classes to verify if certain views were found.

    Use prefix to filter by particular class based views:

    >>> get_class_based_view_urls_matching_url("/some-url", prefix=view_is_subclass(TrackedModelDetailMixin))

    :param url_start: First part of URL
    :param prefix: A prefix function to filter class based views with.
    :param assert_contains_view_classes: Optional list of views, if any are not present an assertion is raise.
    :return: List of tuples of (view, url_pattern)
    """
    valid_url = view_url_pattern_starts_with(url_start)

    def _prefix(**kwargs):
        return valid_url(**kwargs) and prefix(**kwargs)

    view_urls = list(get_class_based_view_urls(prefix=_prefix))

    # Fail if there are no matching views - it indicates the test has a bug.
    assert len(view_urls), f"Did not find any views with a url matching {url_start}"

    if assert_contains_view_classes:
        # Optional list of views that should be under the URL
        view_classes = [view.view_class for view, url in view_urls]
        assert set(assert_contains_view_classes).issubset(view_classes), (
            f"View classes: {assert_contains_view_classes} not "
            f"found in urls: {view_urls} "
        )

    return view_urls


def get_view_model(view_class, override_models):
    """
    :return view_model from a view class, if the fully qualified classname is present inf override_models
    this is returned instead.
    """
    # User may supply their own model in the override_models dict, keyed by the view_class
    fq_class_name = fully_qualified_classname(view_class)
    if fq_class_name in override_models:
        return override_models[fq_class_name]

    if view_class.model:
        # Class Based views (such as Tamato's detail views)
        return view_class.model

    if issubclass(view_class, FilterView):
        # FilterViews (such as TamatoListView)
        return view_class.filterset_class.Meta.model

    raise NotImplemented(f"Retrieving model from {view_class} is not implemented.")


def get_fields_dict(instance, field_names):
    """
    Retrieve dict of fields from django model instance, fetching data via the
    double underscore __ linked models.

    :param instance: Django model instance.
    :param field_names: List of fields to retrieve.
    :return: dict of {field_name: field_value}
    """
    return dict(get_field_tuple(instance, name) for name in field_names)


def view_urlpattern_ids(param):
    """
    Function to use as ids= parameter for tests parameterized by sequences of
    tuples (view, url_pattern)

    Parameterizer functions that generate tuples like this include:
     - get_class_based_view_urls and
     - get_class_based_view_urls_matching_url.

    Note:  List views have no parameters, so the test ids
           there trailing hyphens: -.
    """
    if hasattr(param, "view_class"):
        return param.view_class.__name__
    elif isinstance(param, tuple) and len(param) == 4:
        # tuple containing:
        #   (bits, p_pattern, default_args, pattern_converters)
        #   See: django resolver.reverse_dict implementation
        bits = param[0]
        url_params = bits[0][1]
        return "-".join(url_params)


@lru_cache(maxsize=None)
def _unresolvable_objects(fully_qualified_names):
    """
    Given a tuple of fully_qualified_names, return a list of those that cannot
    be resolved. fully_qualified_names must be a hashable collection such as a
    tuple so results can be cached.

    :param fully_qualified_names: tuple of fully qualified object names.
    """
    not_present = []

    for fq_name in fully_qualified_names:
        module_name, class_name = fq_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        if not hasattr(module, class_name):
            not_present.append(fq_name)

    return not_present


def assert_objects_resolvable(fully_qualified_names):
    """
    Verify that every item in a list is an object that can resolved by
    module_name.object_name.

    :param fully_qualified_names: sequence of full qualified module.class names
    """
    unresolvable = _unresolvable_objects(tuple(fully_qualified_names))
    if unresolvable:
        pytest.fail(
            "Could not resolve objects: " + ", ".join(unresolvable),
        )


def assert_model_view_renders(
    view,
    url_pattern,
    valid_user_client,
    override_models: Optional[Dict[str, ModelBase]] = None,
):
    """
    Integration test to verify class based views.

    Given a class based view and a url_pattern -
      - Lookup the views model and relevant factory.
      - Create data from the factory.
      - Fetch data from the a URL constructed using the just created data.
      - Assert that a 200 status was returned.

    :param view: View for Class based model view
    :param url_pattern:  url_pattern tuple of (bits, p_pattern, default_args, pattern_converters), see django resolver reverse_dict.
    :param valid_user_client:
    :param override_models: dict of {fq_view_name: Model}
    """
    if override_models:
        assert_objects_resolvable(override_models.keys())

    # Before calling the models view, create data by calling the corresponding factory:
    model = get_view_model(view.view_class, override_models or {})

    factory_class_name = f"{model.__name__}Factory"
    factory = getattr(factories, factory_class_name, None)
    assert factory is not None, f"Factory not found: factories.{factory_class_name}"

    instance = factory.create()

    # Build URL using fields from the model.
    # An error retrieving model fields may indicate the class-based-view's
    # model is not what is needed to fill out the URL.
    # Models can be overridden using the override_models parameter.
    bits = url_pattern[0]
    params = get_fields_dict(instance, bits[0][1])
    url = bits[0][0] % params

    assert len(url) > 1, "No matching URLs were found."

    response = valid_user_client.get(f"/{url}")

    assert (
        response.status_code == 200
    ), f"View returned an error status: {response.status_code}"


def assert_records_match(
    expected: TrackedModel,
    imported: TrackedModel,
    ignore=frozenset(),
):
    """
    Asserts that every value for every field in the imported model is the same
    as the data in the expected model.

    System fields that will change from model to model are not checked. Any
    field names given to `ignore` will also not be checked.
    """
    expected_data = get_checkable_data(expected, ignore=ignore)
    imported_data = get_checkable_data(imported, ignore=ignore)
    assert expected_data == imported_data


def assert_many_records_match(
    expected: Sequence[TrackedModel],
    imported: Sequence[TrackedModel],
    ignore=frozenset(),
):
    """
    Asserts that every value for every field in the imported models is the same
    as the data in the expected models, and that the count of both is equal.

    System fields that will change from model to model are not checked. Any
    field names given to `ignore` will also not be checked.
    """
    expected_data = [get_checkable_data(e, ignore=ignore) for e in expected]
    imported_data = [get_checkable_data(i, ignore=ignore) for i in imported]
    assert expected_data == imported_data


def generate_test_import_xml(obj: dict) -> BytesIO:
    last_transaction = Transaction.objects.last()
    next_transaction_id = (last_transaction.order if last_transaction else 0) + 1
    xml = render_to_string(
        template_name="workbaskets/taric/transaction_detail.xml",
        context={
            "envelope_id": next_transaction_id,
            "tracked_models": [obj],
            "transaction_id": next_transaction_id,
            "message_counter": counter_generator(),
            "counter_generator": counter_generator,
        },
    )

    return BytesIO(xml.encode())


def export_workbasket(valid_user_api_client, workbasket):
    response = valid_user_api_client.get(
        reverse(
            "workbaskets:workbasket-detail",
            kwargs={"pk": workbasket.pk},
        ),
        {"format": "xml"},
    )

    assert response.status_code == 200
    return etree.XML(response.content)  # type: ignore


def serialize_xml(xml: etree._Element) -> BytesIO:
    io = BytesIO()
    xml.getroottree().write(io, encoding="utf-8")
    io.seek(0)
    return io


def taric_xml_record_codes(xml):
    """Yields tuples of (record_code, subrecord_code)"""
    records = xml.xpath(".//*[local-name() = 'record']")
    codes = etree.XPath(
        ".//*[local-name()='record.code' or local-name()='subrecord.code']/text()",
    )

    return [tuple(codes(record)) for record in records]


def validate_taric_xml(
    factory=None,
    instance=None,
    factory_kwargs=None,
    check_order=True,
):
    """
    Decorator that creates a fixture named 'xml' and validates end-to-end from
    data creation to xml output.

    The implementation from the supplied factory and returns xml via the test
    client by hitting the workbasket-detail endpoint to return an approved
    workbasket.
    """

    def decorator(func):
        def wraps(
            valid_user_api_client,
            taric_schema,
            approved_transaction,
            *args,
            **kwargs,
        ):
            if not factory and not instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided",
                )
            if factory and instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided - not both.",
                )

            current_instance = instance or factory.create(
                transaction=approved_transaction, **factory_kwargs or {}
            )

            xml = export_workbasket(
                workbasket=approved_transaction.workbasket,
                valid_user_api_client=valid_user_api_client,
            )

            taric_schema.validate(xml)

            assert not taric_schema.error_log, f"XML errors: {taric_schema.error_log}"

            if check_order:
                validate_taric_xml_record_order(xml)

            kwargs = {"xml": xml, **kwargs}

            func(
                *args,
                **kwargs,
            )

        return wraps

    return decorator


class Dates:
    deltas = {
        "normal": (relativedelta(), relativedelta(months=+1)),
        "earlier": (relativedelta(years=-1), relativedelta(years=-1, months=+1)),
        "later": (
            relativedelta(years=+1, months=+1, days=+1),
            relativedelta(years=+1, months=+2),
        ),
        "big": (relativedelta(years=-2), relativedelta(years=+2, days=+1)),
        "adjacent": (relativedelta(days=+1), relativedelta(months=+1)),
        "adjacent_earlier": (relativedelta(months=-1), relativedelta(days=-1)),
        "adjacent_later": (relativedelta(months=+1, days=+1), relativedelta(months=+2)),
        "adjacent_no_end": (relativedelta(months=+1, days=+1), None),
        "adjacent_even_later": (
            relativedelta(months=+2, days=+1),
            relativedelta(months=+3),
        ),
        "adjacent_earlier_big": (
            relativedelta(years=-2, months=-2),
            relativedelta(years=-2),
        ),
        "adjacent_later_big": (
            relativedelta(months=+1, days=+1),
            relativedelta(years=+2, months=+2),
        ),
        "overlap_normal": (
            relativedelta(days=+15),
            relativedelta(days=+14, months=+1, years=+1),
        ),
        "overlap_normal_earlier": (
            relativedelta(months=-1, days=+14),
            relativedelta(days=+14),
        ),
        "overlap_normal_same_year": (
            relativedelta(days=+15),
            relativedelta(days=+14, months=+1),
        ),
        "overlap_big": (relativedelta(years=+1), relativedelta(years=+3, days=+2)),
        "after_big": (
            relativedelta(years=+3, months=+1),
            relativedelta(years=+3, months=+2),
        ),
        "backwards": (relativedelta(months=+1), relativedelta(days=+1)),
        "starts_with_normal": (relativedelta(), relativedelta(days=+14)),
        "ends_with_normal": (relativedelta(days=+14), relativedelta(months=+1)),
        "current": (relativedelta(weeks=-4), relativedelta(weeks=+4)),
        "future": (relativedelta(weeks=+10), relativedelta(weeks=+20)),
        "no_end": (relativedelta(), None),
        "normal_first_half": (relativedelta(), relativedelta(days=+14)),
    }

    @property
    def now(self):
        return self.datetime_now.date()

    @property
    def datetime_now(self):
        return datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    def __getattr__(self, name):
        if name in self.deltas:
            start, end = self.deltas[name]
            start = self.now + start
            if end is not None:
                end = self.now + end
            return TaricDateRange(start, end)
        raise AttributeError(name)

    @classmethod
    def short_before(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(days=-14),
        )

    @classmethod
    def medium_before(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(days=-1),
        )

    @classmethod
    def short_after(cls, dt):
        return TaricDateRange(
            dt + relativedelta(days=+14),
            dt + relativedelta(months=+1),
        )

    @classmethod
    def short_overlap(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(months=+1),
        )

    @classmethod
    def no_end_before(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            None,
        )


def only_applicable_after(cutoff):
    """
    Decorator which asserts that a test fails after a specified cutoff date.

    :param cutoff: A date string, or datetime object before which the test should fail.
    """

    cutoff = parse_date(cutoff)

    def decorator(fn):
        @wraps(fn)
        def do_test(*args, **kwargs):
            # test should pass normally
            fn(*args, **kwargs)

            # test should fail before cutoff
            with freeze_time(cutoff + relativedelta(days=-1)):
                try:
                    fn(*args, **kwargs)

                except pytest.fail.Exception:
                    pass

                except Exception:
                    raise

                else:
                    pytest.fail(f"Rule applied before {cutoff:%Y-%m-%d}")

            return True

        return do_test

    return decorator


def date_post_data(name: str, date: date) -> Dict[str, int]:
    """Construct a POST data fragment for the validity period start and end
    dates of a ValidityPeriodForm from the given date objects."""
    return {
        f"{name}_{i}": part for i, part in enumerate([date.day, date.month, date.year])
    }


def valid_between_start_delta(**delta) -> Callable[[TrackedModel], Dict[str, int]]:
    """Returns updated form data with the delta added to the "lower" date of the
    model's valid between."""
    return lambda model: date_post_data(
        "start_date",
        model.valid_between.lower + relativedelta(**delta),
    )


def valid_between_end_delta(**delta) -> Callable[[TrackedModel], Dict[str, int]]:
    """Returns updated form data with the delta added to the "upper" date of the
    model's valid between."""
    return lambda model: date_post_data(
        "end_date",
        model.valid_between.upper + relativedelta(**delta),
    )


def validity_start_delta(**delta) -> Callable[[TrackedModel], Dict[str, int]]:
    """Returns updated form data with the delta added to the "validity start"
    date of the model."""
    return lambda model: date_post_data(
        "validity_start",
        model.validity_start + relativedelta(**delta),
    )


def validity_period_post_data(start: date, end: date) -> Dict[str, int]:
    """
    Construct a POST data fragment for the validity period start and end dates
    of a ValidityPeriodForm from the given date objects, eg:

    >>> validity_period_post_data(
    >>>     datetime.date(2021, 1, 2),
    >>>     datetime.date(2022, 3, 4),
    >>> )
    {
        "start_date_0": 1,
        "start_date_1": 2,
        "start_date_2": 2021,
        "end_date_0": 4,
        "end_date_1": 3,
        "end_date_2": 2022,
    }
    """
    return {
        **date_post_data("start_date", start),
        **date_post_data("end_date", end),
    }


def get_form_data(form: forms.ModelForm) -> Dict[str, Any]:
    """Returns a dictionary of the fields that the form will put onto a page and
    their current values, taking account of any fields that have sub-fields and
    hence result in multiple HTML <input> objects."""

    data = {**form.initial}
    for field in form.rendered_fields:
        value = data[field] if field in data else form.fields[field].initial
        if hasattr(form.fields[field].widget, "decompress"):
            # If the widget can be decompressed, then it is not just a simple
            # value and has some internal structure. So we need to generate one
            # form item per decompressed value and append the name with _0, _1,
            # etc. This mirrors the MultiValueWidget in django/forms/widgets.py.
            if field in data:
                del data[field]
            value = form.fields[field].widget.decompress(value)
            data.update(
                **{f"{field}_{i}": v for i, v in enumerate(value) if v is not None}
            )
        elif value is not None:
            data.setdefault(field, value)
    return data


def assert_transaction_order(transactions):
    """Given a sequence of transactions verify the default ordering is
    partition, order (assumptions elsewhere in the code may break if this is not
    the case)."""
    assert sorted(transactions, key=lambda o: (o.partition, o.order)) == list(
        transactions,
    ), "Transactions should be in the order partition, order"


def wrap_numbers_over_max_digits(number: int, max_digits):
    """
    Wrap a number if it is too large to fit in the given number of digits.

    Negative numbers use one of the digits for the sign.
    """
    assert max_digits > 0

    if number >= 0:
        return number % (10**max_digits)

    # For negative numbers one digit is reserved for the sign.
    return number % -(10 ** (max_digits - 1))
