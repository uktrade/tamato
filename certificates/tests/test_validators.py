import pytest

from certificates import validators
from common.tests.util import check_validator


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("AAA", True),
        ("ABC", True),
        ("A12", True),
        ("2A1", True),
        ("", False),
        ("0", False),
        ("A", False),
        ("AA", False),
        ("00", False),
        ("0000", False),
        ("000000", False),
        ("AAAAA", False),
        ("aaa", False),
        ("_12", False),
        ("   ", False),
    ],
)
def test_valid_certificate_sid(value, expected_valid):
    check_validator(validators.certificate_sid_validator, value, expected_valid)


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("A", True),
        ("B", True),
        ("0", True),
        ("1", True),
        ("", False),
        ("00", False),
        ("11 ", False),
        ("AA", False),
        ("BB", False),
        ("a", False),
        ("_", False),
        (" ", False),
        ("   ", False),
    ],
)
def test_valid_certificate_type_sid(value, expected_valid):
    check_validator(validators.certificate_type_sid_validator, value, expected_valid)
