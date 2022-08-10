import xml.etree.ElementTree as etree

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.views import HealthCheckResponse

pytestmark = pytest.mark.django_db


def test_index_displays_workbasket_action_form(valid_user_client):
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert "What would you like to do?" in page.select("legend")[0].text
    assert "Edit an existing workbasket" in page.select("label")[1].text
    assert "Create a new workbasket" in page.select("label")[0].text


@pytest.mark.parametrize(
    ("data", "response_url"),
    (
        (
            {
                "workbasket_action": "EDIT",
            },
            "workbaskets:workbasket-ui-list",
        ),
        (
            {
                "workbasket_action": "CREATE",
            },
            "workbaskets:workbasket-ui-create",
        ),
    ),
)
def test_workbasket_action_form_response_redirects_user(
    valid_user,
    client,
    data,
    response_url,
):
    client.force_login(valid_user)
    response = client.post(reverse("home"), data)
    assert response.status_code == 302
    assert response.url == reverse(response_url)


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
