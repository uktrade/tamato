import pytest

from common.tests.util import check_validator
from commodities import validators


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("0100000000", True),
        ("0101010101", True),
        ("1234567890", True),
        ("0000000000", True),
        ("000000000", False),
        ("123456789", False),
        ("ABCDEFGHIJ", False),
        ("01020304AB", False),
        ("", False),
        ("_", False),
        (" ", False),
        ("   ", False),
        ("01020 30405", False),
        ("010203040a", False),
    ],
)
def test_valid_item_id(value, expected_valid):
    check_validator(validators.item_id_validator, value, expected_valid)


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("80", True),
        ("20", True),
        ("11", True),
        ("00", True),
        ("", False),
        ("AA", False),
        ("1 ", False),
        ("1A", False),
        ("B", False),
        ("_", False),
        (" ", False),
        ("   ", False),
    ],
)
def test_valid_suffix(value, expected_valid):
    check_validator(validators.suffix_validator, value, expected_valid)
