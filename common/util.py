"""
Miscellaneous utility functions
"""
from psycopg2.extras import DateTimeTZRange


def is_truthy(value: str) -> bool:
    return str(value).lower() not in ("", "n", "no", "off", "f", "false", "0")


class TaricDateTimeRange(DateTimeTZRange):
    def __init__(self, lower=None, upper=None, bounds="[]", empty=False):
        if not upper:
            bounds = "[)"
        super().__init__(lower, upper, bounds, empty)


def validity_range_contains_range(
    overall_range: DateTimeTZRange, contained_range: DateTimeTZRange
) -> bool:
    """
    If the contained_range has both an upper and lower bound, check they are both
    within the overall_range.

    If either end is unbounded in the contained range,it must also be unbounded in the overall range.
    """
    # XXX assumes both ranges are [] (inclusive-lower, inclusive-upper)

    if overall_range.lower_inf and overall_range.upper_inf:
        return True

    if (contained_range.lower_inf and not overall_range.lower_inf) or (
        contained_range.upper_inf and not overall_range.upper_inf
    ):
        return False

    if not overall_range.lower_inf:
        if (
            not contained_range.upper_inf
            and contained_range.upper < overall_range.lower
        ):
            return False

        if contained_range.lower < overall_range.lower:
            return False

    if not overall_range.upper_inf:
        if (
            not contained_range.lower_inf
            and contained_range.lower > overall_range.upper
        ):
            return False

        if contained_range.upper > overall_range.upper:
            return False

    return True
