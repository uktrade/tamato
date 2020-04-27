"""
Miscellaneous utility functions
"""
from datetime import datetime
from datetime import timezone


BREXIT_DATE = datetime(2021, 1, 1, tzinfo=timezone.utc)


def is_truthy(value: str) -> bool:
    return str(value).lower() not in ("", "n", "no", "off", "f", "false", "0")
