import pytest

from common.tariffs_api import QUOTAS
from common.tariffs_api import async_get_all
from common.tariffs_api import build_urls
from common.tariffs_api import get_quota_data
from common.tariffs_api import serialize_quota_data
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def quota_definitions(quota_order_number):
    return factories.QuotaDefinitionFactory.create_batch(
        5,
        order_number=quota_order_number,
    )


def test_get_quota_data_error(quota_order_number, requests_mock):
    requests_mock.get(url=QUOTAS, status_code=400)
    data = get_quota_data(quota_order_number.id)
    assert data is None


async def test_get_quota_data_ok(quota_order_number, requests_mock, quotas_json):
    requests_mock.get(url=QUOTAS, json=quotas_json, status_code=200)
    data = get_quota_data(quota_order_number.id)
    assert data == quotas_json


@pytest.mark.asyncio
async def test_async_get_all(
    mock_aioresponse,
    quota_order_number,
    quota_definitions,
    quotas_json,
):
    urls = build_urls(quota_order_number.order_number, quota_definitions)
    for url in urls:
        mock_aioresponse.get(url, status=200, payload=quotas_json)
    data = await async_get_all(urls)
    assert data
    for d in data:
        assert d == quotas_json


@pytest.mark.asyncio
async def test_async_get_all_failure(
    mock_aioresponse,
    quota_order_number,
    quota_definitions,
    quotas_json,
):
    urls = build_urls(quota_order_number.order_number, quota_definitions)
    for url in urls:
        mock_aioresponse.get(url, status=400, payload=quotas_json)
    data = await async_get_all(urls)
    assert data
    for d in data:
        assert d == None


def test_build_urls(quota_order_number, quota_definitions):
    urls = build_urls(quota_order_number.order_number, quota_definitions)
    assert len(urls) == 5
    for i, url in enumerate(urls):
        assert QUOTAS in url
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
    serialized = serialize_quota_data(data)
    assert len(serialized) == 3
    assert not set(serialized.keys()).difference({"1111", "2222", "3333"})
    assert serialized["1111"]["status"] == "Open"
    assert serialized["1111"]["balance"] == "80601000.0"
    assert serialized["2222"]["status"] == "Open"
    assert serialized["2222"]["balance"] == "23401000.0"
    assert serialized["3333"]["status"] == "Open"
    assert serialized["3333"]["balance"] == "78849000.0"
