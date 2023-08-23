import asyncio
from enum import Enum
from urllib.parse import urlencode

import aiohttp
import requests

BASE_URL = "https://www.trade-tariff.service.gov.uk/api/v2/"


class Endpoints(Enum):
    QUOTAS = f"{BASE_URL}quotas/search"
    """
    GET /quotas/search Retrieves a list of quota definitions Retrieves a
    paginated list of quota definitions, optionally filtered by a variety of
    parameters.

    https://api.trade-tariff.service.gov.uk/reference.html#get-quotas-search
    """
    COMMODITIES = f"{BASE_URL}commodities/"
    """
    GET /commodities/{id} Retrieves a commodity This resource represents a
    single commodity.

    For this resource, id is a goods_nomenclature_item_id and it is used to
    uniquely identify a commodity and request it from the API. id should be a
    string of ten (10) digits.
    https://api.trade-tariff.service.gov.uk/reference.html#get-commodities-id
    """


def parse_response(response):
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_commodity_data(id):
    url = f"{Endpoints.COMMODITIES.value}{id}"
    print(url)
    return parse_response(requests.get(url))


def get_quota_data(params):
    params = urlencode({**params})
    url = f"{Endpoints.QUOTAS.value}?{params}"
    return parse_response(requests.get(url))


async def async_get(url, session):
    async with session.get(url=url) as response:
        try:
            assert response.status == 200
        except AssertionError:
            return None
        return await response.json()


async def async_get_all(urls):
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[async_get(url, session) for url in urls])


def build_quota_definition_urls(order_number, object_list):
    params = [
        {
            "order_number": order_number,
            "year": d.valid_between.lower.year,
            "month": d.valid_between.lower.month,
            "day": d.valid_between.lower.day,
        }
        for d in object_list
    ]
    return [f"{Endpoints.QUOTAS.value}?{urlencode(p)}" for p in params]


def serialize_quota_data(data):
    json_data = [
        json["data"][0]["attributes"] for json in data if json and json["data"]
    ]

    serialized = {
        json["quota_definition_sid"]: {
            "status": json["status"],
            "balance": json["balance"],
        }
        for json in json_data
    }

    return serialized


def get_quota_definitions_data(order_number, object_list):
    """
    Since the API does not return all definition periods past and future from
    one endpoint we need to make multiple requests with different params.

    We use the quota order number and start date of each of its definition
    periods to build urls to get the data for all of them.
    """

    urls = build_quota_definition_urls(order_number, object_list)

    data = asyncio.run(async_get_all(urls))

    return serialize_quota_data(data)
