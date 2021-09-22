import xml.etree.ElementTree as etree

import pytest
from django.urls import reverse

from common.tests import factories
from common.views import HealthCheckResponse
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_index_creates_workbasket_if_needed(valid_user_client, approved_workbasket):
    assert WorkBasket.objects.is_not_approved().count() == 0
    response = valid_user_client.get(reverse("index"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1


def test_index_doesnt_creates_workbasket_if_not_needed(
    valid_user_client,
    new_workbasket,
):
    assert WorkBasket.objects.is_not_approved().count() == 1
    response = valid_user_client.get(reverse("index"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1


@pytest.mark.parametrize(
    "response, status_code, status",
    [
        (HealthCheckResponse(), 200, "OK"),
        (HealthCheckResponse().fail("Not OK"), 503, "Not OK"),
    ],
)
def test_healthcheck_response(response, status_code, status):
    assert response.status_code == status_code
    payload = etree.fromstring(response.content)
    assert payload.tag == "pingdom_http_custom_check"
    assert payload[0].tag == "status"
    assert payload[0].text == status
    assert payload[1].tag == "response_time"


def test_handles_multiple_unapproved_workbaskets(valid_user_client, new_workbasket):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    transaction = factories.TransactionFactory.create(workbasket=workbasket)
    with transaction:
        factories.FootnoteTypeFactory.create_batch(2)

    assert WorkBasket.objects.is_not_approved().count() == 2

    response = valid_user_client.get(reverse("index"))

    assert response.status_code == 200
