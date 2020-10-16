from datetime import datetime
from datetime import timezone

import pytest
from psycopg2._range import DateTimeTZRange

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
            Dates.big,
            Dates.normal,
            True,
        ),
        (
            Dates.normal,
            Dates.starts_with_normal,
            True,
        ),
        (
            Dates.normal,
            Dates.ends_with_normal,
            True,
        ),
        (
            Dates.normal,
            Dates.overlap_normal,
            False,
        ),
        (
            Dates.normal,
            Dates.overlap_normal_earlier,
            False,
        ),
        (
            Dates.normal,
            Dates.adjacent_earlier,
            False,
        ),
        (
            Dates.normal,
            Dates.adjacent_later,
            False,
        ),
        (
            Dates.normal,
            Dates.big,
            False,
        ),
        (
            Dates.normal,
            Dates.earlier,
            False,
        ),
        (
            Dates.normal,
            Dates.later,
            False,
        ),
        (
            Dates.normal,
            Dates.normal,
            True,
        ),
    ],
)
def test_validity_range_contains_range(overall, contained, expected):
    assert util.validity_range_contains_range(overall, contained) == expected
