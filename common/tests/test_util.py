from unittest import mock

import pytest

from common import util
from common.tests import factories
from common.tests import models
from common.tests.util import Dates

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "value, expected",
    [
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


def test_identifying_fields(sample_model):
    assert util.get_identifying_fields(sample_model) == {"sid": sample_model.sid}


def test_identifying_fields_to_string(sample_model):
    assert (
        util.get_identifying_fields_to_string(sample_model) == f"sid={sample_model.sid}"
    )


def test_identifying_fields_unique(sample_model):
    assert util.get_identifying_fields_unique(sample_model)
