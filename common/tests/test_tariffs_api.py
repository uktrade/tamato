from unittest.mock import patch

import pytest
import requests
import requests_mock

from common.tariffs_api import Endpoints
from common.tariffs_api import build_quota_definition_urls
from common.tariffs_api import deserialize_quota_data
from common.tariffs_api import get_quota_data
from common.tariffs_api import threaded_get_from_endpoint
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def quota_definitions(quota_order_number):
    return factories.QuotaDefinitionFactory.create_batch(
        5,
        order_number=quota_order_number,
    )


def test_get_quota_data_error(quota_order_number, requests_mock):
    requests_mock.get(url=Endpoints.QUOTAS.value, status_code=400)
    data = get_quota_data({"order_number": quota_order_number.id})
    assert data is None


async def test_get_quota_data_ok(quota_order_number, requests_mock, quotas_json):
    requests_mock.get(url=Endpoints.QUOTAS.value, json=quotas_json, status_code=200)
    data = get_quota_data({"order_number": quota_order_number.id})
    assert data == quotas_json


@pytest.mark.parametrize(
    "has_json_payload, response_status",
    [
        (True, 200),
        (False, 200),
        (False, 404),
    ],
)
@patch("common.tariffs_api.threaded_get_request_session")
def test_threaded_get_from_endpoint(
    get_thread_request_session_mock,
    quotas_json,
    has_json_payload,
    response_status,
):
    """Test that threaded_get_from_endpoint correctly handles HTTP responses and
    JSON payloads."""

    url = Endpoints.QUOTAS.value

    # Create a requests.Session instance and associate it with our
    # requests_mock.Mocker instance, allowing requests mock to associate it
    # as part of its transport replacement when handling requests API calls.
    session = requests.Session()

    with requests_mock.Mocker(session=session) as requests_mocker:
        get_thread_request_session_mock.return_value = session
        requests_mocker.get(
            url=url,
            json=quotas_json if has_json_payload else None,
            status_code=response_status,
        )

        returned_json = threaded_get_from_endpoint(url)
        expected_json = quotas_json if has_json_payload else None

        assert returned_json == expected_json


@patch("common.tariffs_api.threaded_get_request_session")
def test_threaded_get_from_endpoint_network_error(
    get_thread_request_session_mock,
):
    """Test that threaded_get_from_endpoint correctly handles a network
    error."""

    url = Endpoints.QUOTAS.value

    # Create a requests.Session instance and associate it with our
    # requests_mock.Mocker instance, allowing requests mock to associate it
    # as part of its transport replacement when handling requests API calls.
    session = requests.Session()

    # Create an adapter, register url with an associated connection error status
    # against it and mount it on the session.
    adapter = requests_mock.Adapter()
    adapter.register_uri("GET", url, exc=requests.exceptions.ConnectTimeout)
    session.mount(url, adapter=adapter)

    with requests_mock.Mocker(session=session) as requests_mocker:
        get_thread_request_session_mock.return_value = session
        requests_mocker.get(url=url)

        returned_json = threaded_get_from_endpoint(url)

        assert returned_json == None


def test_build_quota_definition_urls(quota_order_number, quota_definitions):
    urls = build_quota_definition_urls(
        quota_order_number.order_number,
        quota_definitions,
    )
    assert len(urls) == 5
    for i, url in enumerate(urls):
        assert "quotas" in url
        assert str(quota_definitions[i].valid_between.lower.year) in url
        assert str(quota_definitions[i].valid_between.lower.month) in url
        assert str(quota_definitions[i].valid_between.lower.day) in url


def test_serialize_quota_data():
    data = [
        {
            "data": [
                {
                    "id": "23098",
                    "type": "definition",
                    "attributes": {
                        "quota_definition_sid": "1111",
                        "quota_order_number_id": "058007",
                        "initial_volume": "80601000.0",
                        "validity_start_date": "2022-07-01T00:00:00.000Z",
                        "validity_end_date": "2022-09-30T23:59:59.000Z",
                        "status": "Open",
                        "description": None,
                        "balance": "80601000.0",
                        "measurement_unit": "Kilogram (kg)",
                        "monetary_unit": None,
                        "measurement_unit_qualifier": None,
                        "last_allocation_date": None,
                        "suspension_period_start_date": None,
                        "suspension_period_end_date": None,
                        "blocking_period_start_date": None,
                        "blocking_period_end_date": None,
                    },
                    "relationships": {
                        "incoming_quota_closed_and_transferred_event": {"data": None},
                        "order_number": {
                            "data": {"id": "058007", "type": "order_number"},
                        },
                        "measures": {"data": []},
                        "quota_balance_events": {},
                    },
                },
            ],
            "included": [],
            "meta": {"pagination": {"page": 1, "per_page": 5, "total_count": 1}},
        },
        {
            "data": [
                {
                    "id": "23099",
                    "type": "definition",
                    "attributes": {
                        "quota_definition_sid": "2222",
                        "quota_order_number_id": "058007",
                        "initial_volume": "80601000.0",
                        "validity_start_date": "2022-10-01T00:00:00.000Z",
                        "validity_end_date": "2022-12-31T23:59:59.000Z",
                        "status": "Open",
                        "description": None,
                        "balance": "23401000.0",
                        "measurement_unit": "Kilogram (kg)",
                        "monetary_unit": None,
                        "measurement_unit_qualifier": None,
                        "last_allocation_date": None,
                        "suspension_period_start_date": None,
                        "suspension_period_end_date": None,
                        "blocking_period_start_date": None,
                        "blocking_period_end_date": None,
                    },
                    "relationships": {
                        "incoming_quota_closed_and_transferred_event": {"data": None},
                        "order_number": {
                            "data": {"id": "058007", "type": "order_number"},
                        },
                        "measures": {"data": []},
                        "quota_balance_events": {},
                    },
                },
            ],
            "included": [],
            "meta": {"pagination": {"page": 1, "per_page": 5, "total_count": 1}},
        },
        {
            "data": [
                {
                    "id": "23100",
                    "type": "definition",
                    "attributes": {
                        "quota_definition_sid": "3333",
                        "quota_order_number_id": "058007",
                        "initial_volume": "78849000.0",
                        "validity_start_date": "2023-01-01T00:00:00.000Z",
                        "validity_end_date": "2023-03-31T23:59:59.000Z",
                        "status": "Open",
                        "description": None,
                        "balance": "78849000.0",
                        "measurement_unit": "Kilogram (kg)",
                        "monetary_unit": None,
                        "measurement_unit_qualifier": None,
                        "last_allocation_date": None,
                        "suspension_period_start_date": None,
                        "suspension_period_end_date": None,
                        "blocking_period_start_date": None,
                        "blocking_period_end_date": None,
                    },
                    "relationships": {
                        "incoming_quota_closed_and_transferred_event": {"data": None},
                        "order_number": {
                            "data": {"id": "058007", "type": "order_number"},
                        },
                        "measures": {"data": []},
                        "quota_balance_events": {},
                    },
                },
            ],
            "included": [],
            "meta": {"pagination": {"page": 1, "per_page": 5, "total_count": 1}},
        },
        None,
    ]
    deserialized = deserialize_quota_data(data)
    assert len(deserialized) == 3
    assert not set(deserialized.keys()).difference({"1111", "2222", "3333"})
    assert deserialized["1111"]["status"] == "Open"
    assert deserialized["1111"]["balance"] == "80601000.0"
    assert deserialized["2222"]["status"] == "Open"
    assert deserialized["2222"]["balance"] == "23401000.0"
    assert deserialized["3333"]["status"] == "Open"
    assert deserialized["3333"]["balance"] == "78849000.0"
