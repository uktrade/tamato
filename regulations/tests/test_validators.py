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
def test_valid_footnote_id(value, expected_valid):
    check_validator(validators.no_information_text_delimiters, value, expected_valid)
