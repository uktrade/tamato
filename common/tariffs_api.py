import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict
from typing import Iterator
from typing import List
from urllib.parse import urlencode

import requests

from quotas.models import QuotaDefinition

_thread_locals = threading.local()
logger = logging.getLogger(__name__)


class URLs(Enum):
    BASE_URL = "https://www.trade-tariff.service.gov.uk/"
    API_URL = f"{BASE_URL}api/v2/"


class Endpoints(Enum):
    QUOTAS = f"{URLs.API_URL.value}quotas/search"
    """
    GET /quotas/search Retrieves a list of quota definitions Retrieves a
    paginated list of quota definitions, optionally filtered by a variety of
    parameters.

    https://api.trade-tariff.service.gov.uk/reference.html#get-quotas-search
    """
    COMMODITIES = f"{URLs.API_URL.value}commodities/"
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
    return parse_response(requests.get(url))


def get_quota_data(params):
    params = urlencode({**params})
    url = f"{Endpoints.QUOTAS.value}?{params}"
    return parse_response(requests.get(url))


def build_quota_definition_urls(
    order_number: str,
    object_list: List[QuotaDefinition],
) -> List[str]:
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


def deserialize_quota_data(data: str) -> Dict:
    """Deserialise JSON formatted data into native Python dictionary format and
    return the result."""

    json_data = [
        json["data"][0]["attributes"] for json in data if json and json["data"]
    ]

    deserialized = {
        json["quota_definition_sid"]: {
            "status": json["status"],
            "balance": json["balance"],
        }
        for json in json_data
    }

    return deserialized


def get_thread_local_request_session() -> requests.Session:
    """Return a requests.Session instance scoped to the current thread."""

    if not hasattr(_thread_locals, "requests_session"):
        _thread_locals.requests_session = requests.Session()
    return _thread_locals.requests_session


def threaded_get_from_endpoint(url: str) -> str:
    """
    Using a `requests.Session` instance per thread, call
    `requests.Session.get()` to query a HTTP API endpoint, given by `url`. JSON
    content is extracted from the response payload and return to the caller.

    If network, service or content errors are encountered, then None is
    returned.
    """

    requests_session = get_thread_local_request_session()
    try:
        with requests_session.get(url) as response:
            response.raise_for_status()
            return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Unable to establish connection during HTTP GET {url}")
        return None
    except requests.exceptions.JSONDecodeError:
        logger.error(f"Can't get JSON content from response to HTTP GET {url}")
        return None
    except requests.exceptions.HTTPError:
        logger.error(
            f"Received error {response.status_code} response to HTTP GET {url}",
        )
        return None
    except Exception as e:
        logger.error(f"Exception encountered while performing HTTP GET {url}")
        logger.error(f"{e}")
        return None


def threaded_get_from_all_endpoints(urls: List[str], max_threads: int = 4) -> Iterator:
    """Return an iterator that can be used to retrieve the JSON content returned
    from each of the endpoints referenced via the URLs in `urls`."""
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        return executor.map(threaded_get_from_endpoint, urls)


def get_quota_definitions_data(
    order_number: str,
    object_list: List[QuotaDefinition],
) -> List[Dict]:
    """
    Since the API does not return all definition periods past and future from
    one endpoint we need to make multiple requests with different params.

    We use the quota order number and start date of each of its definition
    periods to build urls to get the data for all of them.
    """

    urls = build_quota_definition_urls(order_number, object_list)

    # There's normally a maximum of four time periods over which quota data
    # applies - i.e. `object_list` normally contains no more than four
    # QuotaDefinition instances. Therefore use four threads (the default) to
    # retrieve the quota data.
    data = [
        json_content
        for json_content in threaded_get_from_all_endpoints(urls=urls)
        if json_content
    ]

    return deserialize_quota_data(data)
