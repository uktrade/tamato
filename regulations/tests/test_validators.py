import pytest

from common.tests.util import check_validator
from regulations import validators


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("hello world", True),
        ("hello|world", False),
        ("hello\xA0world", False),
        ("hello world\xA0", False),
    ],
)
def test_valid_information_text(value, expected_valid):
    check_validator(validators.no_information_text_delimiters, value, expected_valid)


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("", False),
        ("C123456", False),
        ("Z1234AB", False),
        ("IYY0", False),
        ("C990001A", True),
        ("R2100000", True),
        ("Z2021AAA", True),
        ("V2022ZZZ", True),
        ("IYY12345", True),
        ("C1234567890", False),
    ],
    ids=[
        "empty",
        "too-short",
        "too-short-national",
        "too-short-dummy",
        "valid-1",
        "valid-2",
        "valid-national-1",
        "valid-national-2",
        "valid-dummy",
        "too-long",
    ],
)
def test_valid_regulation_id(value, expected_valid):
    check_validator(validators.regulation_id_validator, value, expected_valid)
