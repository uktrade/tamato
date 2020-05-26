import pytest
from django.core.exceptions import ValidationError

from footnotes import validators


def check_validator(validate, value, expected_valid):
    try:
        validate(value)
    except ValidationError:
        if expected_valid:
            pytest.fail(f'Unexpected validation error for value "{value}"')
    except Exception:
        raise
    else:
        if not expected_valid:
            pytest.fail(f'Expected validation error for value "{value}"')


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
    check_validator(validators.FootnoteIDValidator(), value, expected_valid)


@pytest.mark.parametrize(
    "value, expected_valid",
    [
        ("AA", True),
        ("AAA", True),
        ("AA ", True),
        ("00", False),
        ("000", False),
        ("00 ", False),
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
    check_validator(validators.FootnoteTypeIDValidator(), value, expected_valid)
