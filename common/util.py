"""
Miscellaneous utility functions
"""
from psycopg2.extras import DateTimeTZRange


def is_truthy(value: str) -> bool:
    return str(value).lower() not in ("", "n", "no", "off", "f", "false", "0")


def validity_range_contains_range(
    overall_range: DateTimeTZRange, contained_range: DateTimeTZRange
) -> bool:
    """
    If the contained_range has both an upper and lower bound, check they are both
    within the overall_range.

    If either end is unbounded in the contained range,it must also be unbounded in the overall range.
    """
    if contained_range.upper and contained_range.lower:
        return (
            contained_range.lower in overall_range
            and contained_range.upper in overall_range
        )

    return not (
        (contained_range.upper_inf and overall_range.upper)
        or (contained_range.lower_inf and contained_range.lower)
    )
