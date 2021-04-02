import pytest

from common.tests.util import check_validator
from common.validators import EnvelopeIdValidator
from common.validators import NumberRangeValidator
from common.validators import NumericSIDValidator


@pytest.mark.parametrize(
    ("min", "max", "value", "expected_valid"),
    [
        (0, 10, 5, True),
        (0, 10, 15, False),
        (-10, 0, -5, True),
        (-10, 0, -15, False),
        (6, 6, 6, True),
        (0, 10, 0, True),
        (0, 10, 10, True),
        (0, 10, None, False),
        (0, 10, "0", False),
        (0.0, 10.0, 5.0, True),
        (0.0, 10.0, 5, True),
    ],
)
def test_number_range_validator(min, max, value, expected_valid):
    check_validator(NumberRangeValidator(min, max), value, expected_valid)


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        (-1, False),
        (0, False),
        (1, True),
        (99999999, True),
        (99999999 + 1, False),
    ],
)
def test_numeric_sid_validator(value, expected_valid):
    check_validator(NumericSIDValidator(), value, expected_valid)


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("210001", True),
        ("123456", True),
        ("21001", False),
        ("0A0001", False),
        ("21000A", False),
        ("DIT210001", False),
    ],
)
def test_envelope_id_validator(value, expected_valid):
    check_validator(EnvelopeIdValidator, value, expected_valid)
