import pytest

from tamato import util


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", False),
        ("n", False),
        ("no", False),
        ("off", False),
        ("f", False),
        ("false", False),
        (False, False),
        ("0", False),
        (0, False),
        ("y", True),
        ("yes", True),
        ("on", True),
        ("t", True),
        ("true", True),
        (True, True),
        ("1", True),
        (1, True),
    ]
)
def test_is_truthy(value, expected):
    assert util.is_truthy(value) is expected
