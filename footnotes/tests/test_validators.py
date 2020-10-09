import pytest

from common.tests.util import check_validator
from footnotes import validators


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("000", True),
        ("00000", True),
        ("AAA", False),
        ("", False),
        ("0", False),
        ("A", False),
        ("00", False),
        ("0000", False),
        ("000000", False),
        ("AAAAA", False),
    ],
)
def test_valid_footnote_id(value, expected_valid):
    check_validator(validators.footnote_id_validator, value, expected_valid)


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("AA", True),
        ("AAA", True),
        ("AA ", True),
        ("00", True),
        ("000", True),
        ("00 ", True),
        ("", False),
        ("AAAA", False),
        ("A", False),
        ("0", False),
        (" ", False),
        ("  ", False),
        ("   ", False),
    ],
)
def test_valid_footnote_type_id(value, expected_valid):
    check_validator(validators.footnote_type_id_validator, value, expected_valid)
