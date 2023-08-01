import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.urls import reverse

from common.tests import factories
from common.util import xml_fromstring
from common.views import HealthCheckResponse
from common.views import handler403
from common.views import handler500

pytestmark = pytest.mark.django_db


def test_index_displays_workbasket_action_form(valid_user_client):
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert "Create new workbasket" in page.select("label")[0].text
    assert "Select an existing workbasket" in page.select("label")[1].text
    assert "Package Workbaskets" in page.select("label")[2].text
    assert "Process envelopes" in page.select("label")[3].text
    assert "Search the tariff" in page.select("label")[4].text
    assert "Import EU Taric files" in page.select("label")[5].text


def test_index_displays_logout_buttons_correctly_SSO_off_logged_in(valid_user_client):
    settings.SSO_ENABLED = False
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert page.find_all("a", {"href": "/logout"})


def test_index_redirects_to_login_page_logged_out_SSO_off(client):
    settings.SSO_ENABLED = False
    response = client.get(reverse("home"))

    assert response.status_code == 302
    response.url.startswith(reverse("admin:login"))


def test_index_displays_login_buttons_correctly_SSO_on(valid_user_client):
    settings.SSO_ENABLED = True
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert not page.find_all("a", {"href": "/logout"})
    assert not page.find_all("a", {"href": "/login"})


@pytest.mark.parametrize(
    ("data", "response_url"),
    (
        (
            {
                "workbasket_action": "CREATE",
            },
            "workbaskets:workbasket-ui-create",
        ),
        (
            {
                "workbasket_action": "EDIT",
            },
            "workbaskets:workbasket-ui-list",
        ),
        (
            {
                "workbasket_action": "PACKAGE_WORKBASKETS",
            },
            "publishing:packaged-workbasket-queue-ui-list",
        ),
        (
            {
                "workbasket_action": "PROCESS_ENVELOPES",
            },
            "publishing:envelope-queue-ui-list",
        ),
        (
            {
                "workbasket_action": "SEARCH",
            },
            "search-page",
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
    payload = xml_fromstring(response.content)
    assert payload.tag == "pingdom_http_custom_check"
    assert payload[0].tag == "status"
    assert payload[0].text == status
    assert payload[1].tag == "response_time"


def test_app_info(valid_user_client):
    response = valid_user_client.get(reverse("app-info"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert "Active business rule checks" in page.select("h2")[0].text


def test_index_displays_footer_links(valid_user_client):
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    a_tags = page.select("footer a")

    assert len(a_tags) == 7
    assert "Privacy policy" in a_tags[0].text
    assert (
        a_tags[0].attrs["href"]
        == "https://workspace.trade.gov.uk/working-at-dit/policies-and-guidance/policies/tariff-application-privacy-policy/"
    )


def test_search_page_displays_links(valid_user_client):
    url = reverse("search-page")
    response = valid_user_client.get(url)
    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    links = page.select(".govuk-link")
    assert len(links) == 8


def test_handler403(client):
    request = client.get("/")
    response = handler403(request)

    assert response.status_code == 403
    assert response.template_name == "common/403.jinja"

    user = factories.UserFactory.create()
    client.force_login(user)
    response = client.get(reverse("workbaskets:workbasket-ui-list"))

    assert response.status_code == 403
    assert response.template_name == "common/403.jinja"


def test_handler500(client):
    request = client.get("/")
    response = handler500(request)

    assert response.status_code == 500
    assert response.template_name == "common/500.jinja"


def test_accessibility_statement_view_returns_200(valid_user_client):
    url = reverse("accessibility-statement")
    response = valid_user_client.get(url)

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert (
        "Accessibility statement for the Tariff application platform"
        in page.select("h1")[0].text
    )
