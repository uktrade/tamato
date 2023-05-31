import pytest

from common.tests.util import check_validator
from common.validators import AlphanumericValidator
from common.validators import EnvelopeIdValidator
from common.validators import NumberRangeValidator
from common.validators import NumericSIDValidator
from common.validators import NumericValidator
from common.validators import PasswordPolicyValidator
from common.validators import SymbolValidator


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


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("A Good Description", True),
        ("A Good description with Numbers in 001", True),
        (1234, True),
        ("<Sketchy_Code></>", False),
    ],
)
def test_alphanumeric_validator(value, expected_valid):
    check_validator(AlphanumericValidator, value, expected_valid)


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("Text without symbols is fine", True),
        ("Numbers are also fine 3678767", True),
        ("These specific symbols are fine .,'()&£$%/@!", True),
        ("<Sketchy_Code>This is not fine</>", False),
        ("{{ This is also not [fine] }}", False),
    ],
)
def test_symbol_validator(value, expected_valid):
    check_validator(SymbolValidator, value, expected_valid)


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("Text When There Shouldn't be.", False),
        (1234, True),
        ("<Sketchy_Code></>", False),
        (".,'()&£$%/@!", False),
    ],
)
def test_numeric_validator(value, expected_valid):
    check_validator(NumericValidator, value, expected_valid)


@pytest.mark.parametrize(
    ("value", "expected_valid"),
    [
        ("123", False),
        ("lower", False),
        ("lower123", False),
        ("lower123!", False),
        ("Capital", False),
        ("Capital123", False),
        ("Capital!", False),
        ("CAPITAL123!", False),
        ("Capital123!", True),
    ],
)
def test_password_policy_validator(value, expected_valid):
    validator = PasswordPolicyValidator()
    check_validator(validator.validate, value, expected_valid)
