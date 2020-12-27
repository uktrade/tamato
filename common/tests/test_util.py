import pytest

from common import util
from common.tests.util import Dates


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
