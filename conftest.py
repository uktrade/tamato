from datetime import datetime
from datetime import timezone

import pytest
from lxml import etree
from psycopg2.extras import DateTimeTZRange
from pytest_bdd import given
from rest_framework.test import APIClient

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
    return Dates()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def valid_user(db):
    return factories.UserFactory.create()


@given('a valid user named "Alice"', target_fixture="a_valid_user_called_alice")
def a_valid_user_called_alice():
    return factories.UserFactory.create(username="Alice")


@pytest.fixture
def valid_user_login(client, valid_user):
    client.force_login(valid_user)


@given("I am logged in as Alice", target_fixture="alice_login")
def alice_login(client, a_valid_user_called_alice):
    client.force_login(a_valid_user_called_alice)


@pytest.fixture
def valid_user_api_client(api_client, valid_user) -> APIClient:
    api_client.force_login(valid_user)
    return api_client


@pytest.fixture
def taric_schema(settings) -> etree.XMLSchema:
    with open(settings.TARIC_XSD) as xsd_file:
        return etree.XMLSchema(etree.parse(xsd_file))


@pytest.fixture
def approved_workbasket():
    return factories.TransactionFactory().workbasket
