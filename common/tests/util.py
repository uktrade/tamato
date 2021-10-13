import contextlib
from datetime import date
from datetime import datetime
from datetime import timezone
from functools import wraps
from io import BytesIO
from itertools import count
from typing import Any
from typing import Dict
from typing import Sequence

import pytest
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse
from freezegun import freeze_time
from lxml import etree

from common.models.records import TrackedModel
from common.renderers import counter_generator
from common.serializers import validate_taric_xml_record_order
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
def raises_if(exception, expected):
    try:
        yield
    except exception:
        if not expected:
            raise
    else:
        if expected:
            pytest.fail(f"Did not raise {exception}")


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
    checked_field_names = {f.name for f in model.copyable_fields} - ignore
    data = {
        name: getattr(model, get_accessor(model._meta.get_field(name)))
        for name in checked_field_names
    }
    identifying_fields = {
        name: data[name].get_identifying_fields()
        for name in checked_field_names
        if hasattr(data[name], "get_identifying_fields")
    }
    data.update(identifying_fields)
    return data


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


_transaction_counter = count(start=1)


def generate_test_import_xml(obj: dict) -> BytesIO:

    xml = render_to_string(
        template_name="workbaskets/taric/transaction_detail.xml",
        context={
            "envelope_id": next(_transaction_counter),
            "tracked_models": [obj],
            "transaction_id": next(_transaction_counter),
            "message_counter": counter_generator(),
            "counter_generator": counter_generator,
        },
    )

    return BytesIO(xml.encode())


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
    def decorator(func):
        def wraps(
            api_client,
            taric_schema,
            approved_transaction,
            valid_user,
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

            api_client.force_login(user=valid_user)
            response = api_client.get(
                reverse(
                    "workbaskets:workbasket-detail",
                    kwargs={"pk": approved_transaction.workbasket.pk},
                ),
                {"format": "xml"},
            )

            assert response.status_code == 200

            content = response.content

            xml = etree.XML(content)

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
        f"{name}_{i}": part
        for name, date in (("start_date", start), ("end_date", end))
        for i, part in enumerate([date.day, date.month, date.year])
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
