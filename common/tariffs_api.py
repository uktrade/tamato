import asyncio
from urllib.parse import urlencode

import aiohttp
import requests

BASE_URL = "https://www.trade-tariff.service.gov.uk/api/v2/"
QUOTAS = f"{BASE_URL}quotas/search"


def get_quota_data(order_number):
    params = urlencode({"order_number": order_number})
    response = requests.get(f"{QUOTAS}?{params}")
    if response.status_code == 200:
        return response.json()
    else:
        return None


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


def build_urls(order_number, object_list):
    params = [
        {
            "order_number": order_number,
            "year": d.valid_between.lower.year,
            "month": d.valid_between.lower.month,
            "day": d.valid_between.lower.day,
        }
        for d in object_list
    ]
    return [f"{QUOTAS}?{urlencode(p)}" for p in params]


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

    urls = build_urls(order_number, object_list)

    data = asyncio.run(async_get_all(urls))

    return serialize_quota_data(data)
