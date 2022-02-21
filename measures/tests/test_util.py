import pytest

from measures import util


@pytest.mark.parametrize(
    "value, conversion, expected",
    [
        ("20.000", 2, "40.000"),
        ("1.000", 0.83687, "0.830"),
    ],
)
def test_eur_to_gbp_conversion(value, conversion, expected):
    assert util.convert_eur_to_gbp(value, conversion) == expected
