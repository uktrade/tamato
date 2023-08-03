"""Custom path converters
https://docs.djangoproject.com/en/3.2/topics/http/urls/#registering-custom-path-
converters."""
import datetime

from django.urls.converters import IntConverter

from common.util import TaricDateRange


class NumericSIDConverter(IntConverter):
    """Parses a NumericSID from the path."""

    regex = r"[0-9]{1,8}"


class TaricDateRangeConverter:
    regex = r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}--([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})*"

    def to_python(self, value):
        lower, upper = value.split("--")
        lower_year, lower_month, lower_day = lower.split("-")
        if upper:
            upper_year, upper_month, upper_day = upper.split("-")
            return TaricDateRange(
                datetime.date(int(lower_year), int(lower_month), int(lower_day)),
                datetime.date(int(upper_year), int(upper_month), int(upper_day)),
            )
        return TaricDateRange(
            datetime.date(int(lower_year), int(lower_month), int(lower_day)),
            None,
        )

    def to_url(self, value):
        if value.upper:
            return (
                f"{value.lower.year}-{str(value.lower.month).zfill(2)}-{str(value.lower.day).zfill(2)}"
                f"--{value.upper.year}-{str(value.upper.month).zfill(2)}-{str(value.upper.day).zfill(2)}"
            )
        return f"{value.lower.year}-{str(value.lower.month).zfill(2)}-{str(value.lower.day).zfill(2)}--"
