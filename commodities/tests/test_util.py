import pytest

from commodities import util


@pytest.mark.parametrize(
    "value, expected",
    [
        ("0100000000", "0100000000"),
        ("0200", "0200000000"),
        (100020000, "0100020000"),
        (1234567890, "1234567890"),
        (1000.0, "1000000000"),
        ("12 34 56 78 90", "1234567890"),
        ("1234.56.78", "1234567800"),
        ("1234 56.78.90", "1234567890"),
    ],
)
def test_clean_item_id(value, expected):
    assert util.clean_item_id(value) == expected
