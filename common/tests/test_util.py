import os
from unittest import mock

import pytest
from defusedxml.common import DTDForbidden

from common import util
from common.tests import factories
from common.tests import models
from common.tests.util import Dates
from common.tests.util import wrap_numbers_over_max_digits

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, False),
        (False, False),
        (True, True),
        ("", False),
        ("n", False),
        ("no", False),
        ("off", False),
        ("f", False),
        ("false", False),
        (False, False),
        ("0", False),
        (0, False),
        ("y", True),
        ("yes", True),
        ("on", True),
        ("t", True),
        ("true", True),
        (True, True),
        ("1", True),
        (1, True),
    ],
)
def test_is_truthy(value, expected):
    assert util.is_truthy(value) is expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("str", "str"),
        (1, "1"),
        (2.0, "2"),
        (3.99, "3"),
    ],
)
def test_strint(value, expected):
    assert util.strint(value) == expected


@pytest.mark.parametrize(
    "values, expected",
    [
        ([], None),
        ([None], None),
        ([None, None], None),
        ([0, None], 0),
        ([0, 1], 0),
        ([None, 2, 1], 1),
    ],
)
def test_maybe_min(values, expected):
    assert util.maybe_min(*values) is expected


@pytest.mark.parametrize(
    "values, expected",
    [
        ([], None),
        ([None], None),
        ([None, None], None),
        ([0, None], 0),
        ([0, 1], 1),
        ([None, 2, 1], 2),
    ],
)
def test_maybe_max(values, expected):
    assert util.maybe_max(*values) is expected


@pytest.mark.parametrize(
    "overall,contained,expected",
    [
        (
            "big",
            "normal",
            True,
        ),
        (
            "normal",
            "starts_with_normal",
            True,
        ),
        (
            "normal",
            "ends_with_normal",
            True,
        ),
        (
            "normal",
            "overlap_normal",
            False,
        ),
        (
            "normal",
            "overlap_normal_earlier",
            False,
        ),
        (
            "normal",
            "adjacent_earlier",
            False,
        ),
        (
            "normal",
            "adjacent_later",
            False,
        ),
        (
            "normal",
            "big",
            False,
        ),
        (
            "normal",
            "earlier",
            False,
        ),
        (
            "normal",
            "later",
            False,
        ),
        (
            "normal",
            "normal",
            True,
        ),
    ],
)
def test_validity_range_contains_range(overall, contained, expected):
    dates = Dates()
    overall = getattr(dates, overall)
    contained = getattr(dates, contained)
    assert util.validity_range_contains_range(overall, contained) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("normal", "normal", True),
        ("normal", "overlap_normal", True),
        ("normal", "current", True),
        ("normal", "adjacent_later", False),
    ],
    ids=[
        "identical",
        "overlapped",
        "contained",
        "adjacent",
    ],
)
def test_date_ranges_overlap(date_ranges, a, b, expected):
    dr_a = getattr(date_ranges, a)
    dr_b = getattr(date_ranges, b)
    assert util.date_ranges_overlap(dr_a, dr_b) == expected


@pytest.mark.parametrize(
    "date_range, containing_range, expected_lower, expected_upper",
    [
        ("normal", "normal", "normal", "normal"),
        ("normal", "overlap_normal", "overlap_normal", "normal"),
        ("overlap_normal_earlier", "normal", "normal", "overlap_normal_earlier"),
        ("normal", "big", "normal", "normal"),
        ("normal", "adjacent_later", None, None),
    ],
    ids=[
        "identical",
        "overlapped_later",
        "overlapped_earlier",
        "contained",
        "adjacent",
    ],
)
def test_contained_date_range(
    date_ranges,
    date_range,
    containing_range,
    expected_lower,
    expected_upper,
):
    dr = getattr(date_ranges, date_range)
    dr_containing = getattr(date_ranges, containing_range)
    dr_contained = util.contained_date_range(dr, dr_containing)

    if expected_lower is None:
        assert dr_contained is None
    else:
        dr_start = getattr(date_ranges, expected_lower)
        dr_end = getattr(date_ranges, expected_upper)
        assert dr_contained.lower == dr_start.lower
        assert dr_contained.upper == dr_end.upper


@pytest.mark.parametrize(
    "model_data, field, expected",
    (
        ({"sid": 123}, "sid", 123),
        ({"linked_model__sid": 456}, "linked_model__sid", 456),
        ({"linked_model": None}, "linked_model", None),
        ({"linked_model": None}, "linked_model__sid", None),
    ),
)
def test_get_field_tuple(model_data, field, expected):
    model = factories.TestModel3Factory(**model_data)
    assert util.get_field_tuple(model, field) == (field, expected)


@pytest.fixture
def sample_model() -> models.TestModel1:
    return factories.TestModel1Factory.create()


def test_get_taric_template(sample_model):
    with mock.patch("common.util.loader.get_template"):
        assert util.get_taric_template(sample_model) == "taric/test_model1.xml"


def test_get_model_indefinite_article():
    additional_code = factories.AdditionalCodeFactory()
    measure = factories.MeasureFactory()

    assert util.get_model_indefinite_article(additional_code) == "an"
    assert util.get_model_indefinite_article(measure) == "a"


def test_get_next_id_handles_empty_queryset():
    qs = factories.FootnoteFactory._meta.model.objects.none()
    id_field = factories.FootnoteFactory._meta.model._meta.get_field("footnote_id")
    next_id = util.get_next_id(qs, id_field, 3)

    assert next_id == "001"


@pytest.mark.parametrize(
    "number, max_digits, expected",
    (
        (0, 2, 0),
        (-9, 2, -9),
        (-10, 2, 0),
        (99, 2, 99),
        (100, 2, 0),
        (0, 3, 0),
        (-99, 3, -99),
        (-100, 3, 0),
        (999, 3, 999),
        (1000, 3, 0),
    ),
)
def test_wrap_numbers_over_max_digits(number, max_digits, expected):
    """
    Test some edge cases for wrap_int_at_max_digits.

    Negative numbers use a digit for the sign, which is reflected in the test
    data.
    """
    assert wrap_numbers_over_max_digits(number, max_digits) == expected


def test_parse_xml_dtd():
    file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_files",
        "dtd.xml",
    )
    with pytest.raises(DTDForbidden):
        util.parse_xml(file)


def test_xml_fromstring_dtd():
    xml_string = """<?xml version="1.0" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
    <head/>
    <body>text</body>
</html>"""
    with pytest.raises(DTDForbidden):
        util.xml_fromstring(xml_string)
