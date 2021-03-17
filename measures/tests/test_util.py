import pytest

from measures import util


@pytest.mark.parametrize(
    "value, expected",
    [
        ("6.00 %", "6.00 %"),
        ("1.23 GBP/kg", "1.23 GBP/kg"),
        (0, "0.000%"),
        (1, "100.000%"),
        (0.12, "12.000%"),
        (0.12345, "12.345%"),
        (0.123456789, "12.345%"),
    ],
)
def test_clean_duty_sentence(value, expected):
    assert util.clean_duty_sentence(value) == expected


@pytest.mark.parametrize(
    "value, conversion, expected",
    [
        ("20.000", 2, "40.000"),
        ("1.000", 0.83687, "0.830"),
    ],
)
def test_eur_to_gbp_conversion(value, conversion, expected):
    assert util.convert_eur_to_gbp(value, conversion) == expected
