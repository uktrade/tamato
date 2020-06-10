import pytest

from common.tests.util import check_validator
from geo_areas import validators


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("0000", True),
        ("00", True),
        ("AAAA", True),
        ("AA", True),
        ("A00A", True),
        ("", False),
        ("0", False),
        ("A", False),
        ("000", False),
        ("AAA", False),
        ("00000", False),
        ("AAAAA", False),
        ("aAAA", False),
        ("a000", False),
    ],
)
def test_valid_area_id(value, expected_valid):
    check_validator(validators.area_id_validator, value, expected_valid)
