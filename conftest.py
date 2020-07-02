from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from psycopg2.extras import DateTimeTZRange
from pytest_bdd import given

from common.tests import factories
from common.tests.util import Dates


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
def date_ranges() -> Dates:
    return Dates


@given('a valid user named "Alice"')
def valid_user():
    return factories.UserFactory.create(username="Alice")


@given("I am logged in as Alice")
def valid_user_login(client, valid_user):
    client.force_login(valid_user)
