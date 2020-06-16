from datetime import datetime, timedelta
from datetime import timezone

import pytest
from psycopg2.extras import DateTimeTZRange


@pytest.fixture(
    params=[
        ("2020-05-18", "2020-05-17", True),
        ("2020-05-18", "2020-05-18", False),
        ("2020-05-18", "2020-05-19", False),
    ]
)
def validity_range(request):
    start, end, expect_error = request.param
    return (
        DateTimeTZRange(
            datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
            datetime.fromisoformat(end).replace(tzinfo=timezone.utc),
        ),
        expect_error,
    )


@pytest.fixture
def date_ranges():
    class Dates:
        normal = DateTimeTZRange(
            datetime(2016, 1, 1, tzinfo=timezone.utc),
            datetime(2016, 2, 1, tzinfo=timezone.utc),
        )
        earlier = DateTimeTZRange(
            datetime(2015, 1, 1, tzinfo=timezone.utc),
            datetime(2015, 2, 1, tzinfo=timezone.utc),
        )
        later = DateTimeTZRange(
            datetime(2017, 2, 2, tzinfo=timezone.utc),
            datetime(2017, 3, 1, tzinfo=timezone.utc),
        )
        big = DateTimeTZRange(
            datetime(2014, 1, 1, tzinfo=timezone.utc),
            datetime(2018, 1, 2, tzinfo=timezone.utc),
        )
        overlap_normal = DateTimeTZRange(
            datetime(2016, 1, 15, tzinfo=timezone.utc),
            datetime(2017, 2, 15, tzinfo=timezone.utc),
        )
        overlap_big = DateTimeTZRange(
            datetime(2018, 1, 1, tzinfo=timezone.utc),
            datetime(2019, 1, 3, tzinfo=timezone.utc),
        )
        after_big = DateTimeTZRange(
            datetime(2019, 2, 1, tzinfo=timezone.utc),
            datetime(2019, 3, 1, tzinfo=timezone.utc),
        )
        backwards = DateTimeTZRange(
            datetime(2021, 2, 1, tzinfo=timezone.utc),
            datetime(2021, 1, 2, tzinfo=timezone.utc),
        )
        current = DateTimeTZRange(
            datetime.today() - timedelta(weeks=4), datetime.today() + timedelta(weeks=4)
        )
        future = DateTimeTZRange(
            datetime.today() + timedelta(weeks=10),
            datetime.today() + timedelta(weeks=20),
        )

    return Dates
