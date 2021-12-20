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


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("normal", "normal", True),
        ("normal", "overlap_normal", True),
        ("normal", "current", True),
        ("normal", "adjacent_later", False),
    ],
    ids=[
        "identical",
        "overlapped",
        "contained",
        "adjacent",
    ],
)
def test_date_ranges_overlap(date_ranges, a, b, expected):
    dr_a = getattr(date_ranges, a)
    dr_b = getattr(date_ranges, b)
    assert util.date_ranges_overlap(dr_a, dr_b) == expected


@pytest.mark.parametrize(
    "date_range, containing_range, expected_lower, expected_upper",
    [
        ("normal", "normal", "normal", "normal"),
        ("normal", "overlap_normal", "overlap_normal", "normal"),
        ("overlap_normal_earlier", "normal", "normal", "overlap_normal_earlier"),
        ("normal", "big", "normal", "normal"),
        ("normal", "adjacent_later", None, None),
    ],
    ids=[
        "identical",
        "overlapped_later",
        "overlapped_earlier",
        "contained",
        "adjacent",
    ],
)
def test_contained_date_range(
    date_ranges,
    date_range,
    containing_range,
    expected_lower,
    expected_upper,
):
    dr = getattr(date_ranges, date_range)
    dr_containing = getattr(date_ranges, containing_range)
    dr_contained = util.contained_date_range(dr, dr_containing)

    if expected_lower is None:
        assert dr_contained is None
    else:
        dr_start = getattr(date_ranges, expected_lower)
        dr_end = getattr(date_ranges, expected_upper)
        assert dr_contained.lower == dr_start.lower
        assert dr_contained.upper == dr_end.upper


@pytest.mark.parametrize(
    "date_range, containing_range, contained",
    [
        ("normal", "normal", True),
        ("normal", "overlap_normal", False),
        ("overlap_normal_earlier", "normal", False),
        ("normal", "big", True),
        ("normal", "adjacent_later", False),
    ],
    ids=[
        "identical",
        "overlapped_later",
        "overlapped_earlier",
        "contained",
        "adjacent",
    ],
)
def test_is_contained(
    date_ranges,
    date_range,
    containing_range,
    contained,
):
    """Asserts that is_contained returns the correct result."""
    dr = getattr(date_ranges, date_range)
    dr_containing = getattr(date_ranges, containing_range)

    assert util.is_contained(dr, dr_containing) == contained
