import contextlib
from datetime import datetime, timezone, timedelta

import pytest
from django.core.exceptions import ValidationError
from psycopg2._range import DateTimeTZRange


@contextlib.contextmanager
def raises_if(exception, expected):
    try:
        yield
    except exception:
        if not expected:
            raise
    else:
        if expected:
            pytest.fail(f"Did not raise {exception}")


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


class Dates:
    normal = DateTimeTZRange(
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        datetime(2021, 2, 1, tzinfo=timezone.utc),
    )
    earlier = DateTimeTZRange(
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 2, 1, tzinfo=timezone.utc),
    )
    later = DateTimeTZRange(
        datetime(2022, 2, 2, tzinfo=timezone.utc),
        datetime(2022, 3, 1, tzinfo=timezone.utc),
    )
    big = DateTimeTZRange(
        datetime(2019, 1, 1, tzinfo=timezone.utc),
        datetime(2023, 1, 2, tzinfo=timezone.utc),
    )
    adjacent_earlier = DateTimeTZRange(
        datetime(2020, 12, 1, tzinfo=timezone.utc),
        datetime(2020, 12, 31, tzinfo=timezone.utc),
    )
    adjacent_later = DateTimeTZRange(
        datetime(2022, 2, 1, tzinfo=timezone.utc),
        datetime(2022, 3, 1, tzinfo=timezone.utc),
    )
    overlap_normal = DateTimeTZRange(
        datetime(2021, 1, 15, tzinfo=timezone.utc),
        datetime(2022, 2, 15, tzinfo=timezone.utc),
    )
    overlap_normal_earlier = DateTimeTZRange(
        datetime(2020, 12, 15, tzinfo=timezone.utc),
        datetime(2021, 1, 15, tzinfo=timezone.utc),
    )
    overlap_big = DateTimeTZRange(
        datetime(2022, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 3, tzinfo=timezone.utc),
    )
    after_big = DateTimeTZRange(
        datetime(2024, 2, 1, tzinfo=timezone.utc),
        datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    backwards = DateTimeTZRange(
        datetime(2021, 2, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 2, tzinfo=timezone.utc),
    )
    starts_with_normal = DateTimeTZRange(
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 15, tzinfo=timezone.utc),
    )
    ends_with_normal = DateTimeTZRange(
        datetime(2021, 1, 15, tzinfo=timezone.utc),
        datetime(2021, 2, 1, tzinfo=timezone.utc),
    )
    current = DateTimeTZRange(
        datetime.today() - timedelta(weeks=4), datetime.today() + timedelta(weeks=4)
    )
    future = DateTimeTZRange(
        datetime.today() + timedelta(weeks=10), datetime.today() + timedelta(weeks=20),
    )
    no_end = DateTimeTZRange(datetime(2021, 1, 1, tzinfo=timezone.utc), None)
