import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import modify_settings
from django.test import override_settings
from django.urls import reverse
from django.urls import reverse_lazy

from checks.tests.factories import TrackedModelCheckFactory
from common.tests import factories
from common.util import xml_fromstring
from common.views import HealthCheckResponse
from common.views import handler403
from common.views import handler500
from tasks.models import UserAssignment
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_index_displays_logout_buttons_correctly_SSO_off_logged_in(valid_user_client):
    settings.SSO_ENABLED = False
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    assert page.find("form", {"action": reverse("logout")})


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
    assert not page.find("form", {"action": reverse("logout")})
    assert not page.find_all("a", {"href": "/login"})


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


def test_app_info_non_superuser(valid_user_client):
    """Users without the superuser permission have a restricted view of
    application information."""
    response = valid_user_client.get(reverse("app-info"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    h2_elements = page.select(".info-section h2")

    assert len(h2_elements) == 2
    assert "Active business rule checks" in h2_elements[0].text
    assert "Active envelope generation tasks" in h2_elements[1].text


def test_app_info_superuser(superuser_client, new_workbasket):
    """
    Superusers should have an unrestricted view of application information.

    The new_workbasket fixture provides access to transaction information in the
    deployment infomation section.
    """
    response = superuser_client.get(reverse("app-info"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    h2_elements = page.select(".info-section h2")

    assert len(h2_elements) == 3
    assert "Deployment information" in h2_elements[0].text
    assert "Active business rule checks" in h2_elements[1].text
    assert "Active envelope generation tasks" in h2_elements[2].text


def test_index_displays_footer_links(valid_user_client):
    response = valid_user_client.get(reverse("home"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    a_tags = page.select("footer a")

    assert len(a_tags) == 3
    assert "Accessibility statement" in a_tags[0].text
    assert "Privacy policy" in a_tags[1].text
    assert "Help centre" in a_tags[2].text


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
        "Accessibility statement for the Tariff management tool"
        in page.select("h1")[0].text
    )


@override_settings(MAINTENANCE_MODE=True)
@modify_settings(
    MIDDLEWARE={
        "append": "common.middleware.MaintenanceModeMiddleware",
    },
)
def test_user_redirect_during_maintenance_mode(valid_user_client):
    response = valid_user_client.get(reverse("home"))
    assert response.status_code == 302
    assert response.url == reverse("maintenance")


def test_maintenance_mode_page_content(valid_user_client):
    response = valid_user_client.get(reverse("maintenance"))
    assert response.status_code == 200
    assert "Sorry, the service is unavailable" in str(response.content)


@pytest.mark.parametrize(
    ("card", "permission"),
    [
        ("What would you like to do?", "view_workbasket"),
        ("Currently working on", "change_workbasket"),
        ("EU TARIC files", "add_trackedmodel"),
        ("Envelopes", "consume_from_packaging_queue"),
        ("Resources", ""),
        ("Get help", ""),
        ("Get in touch", ""),
    ],
)
def test_homepage_cards_match_user_permissions(card, permission, client):
    user = factories.UserFactory.create()
    client.force_login(user)

    if permission:
        response = client.get(reverse("home"))
        assert not card in str(response.content)
        user.user_permissions.add(Permission.objects.get(codename=permission))

    response = client.get(reverse("home"))
    assert card in str(response.content)


def test_homepage_cards_contain_expected_links(superuser_client):
    expected_urls = {
        "Create a new workbasket": "workbaskets:workbasket-ui-create",
        "Edit a workbasket": "workbaskets:workbasket-ui-list",
        "Package a workbasket": "publishing:packaged-workbasket-queue-ui-list",
        "Search for workbaskets": "workbaskets:workbasket-ui-list-all",
        "View EU import list": "commodity_importer-ui-list",
        "Process envelopes": "publishing:envelope-queue-ui-list",
        "Measures process queue": "measure-create-process-queue",
        "Application information": "app-info",
        "Importer V1": "import_batch-ui-list",
        "Importer V2": "taric_parser_import_ui_list",
        "TAP reports": "reports:index",
    }
    response = superuser_client.get(reverse("home"))
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    links = [a["href"] for a in page.find_all("a")]

    for url in expected_urls.values():
        assert reverse(url) in links


@pytest.mark.parametrize(
    ("status"),
    [
        (WorkflowStatus.EDITING),
        (WorkflowStatus.ERRORED),
    ],
)
def test_homepage_card_currently_working_on(status, valid_user, valid_user_client):
    workbasket = factories.WorkBasketFactory.create(status=status)
    review_assignment = factories.UserAssignmentFactory.create(
        user=valid_user,
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_REVIEWER,
        task__workbasket=workbasket,
    )
    rule_violation = TrackedModelCheckFactory.create(
        transaction_check__transaction=workbasket.new_transaction(),
        successful=False,
    )

    response = valid_user_client.get(reverse("home"))
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    card = page.find("h3", string="Currently working on")
    assigned_workbasket = card.find_next("a")
    details = card.find_next("span")

    assert f"Workbasket ID {workbasket.pk}" in assigned_workbasket.text
    assert "Reviewing" and "rule violation" in details.text


@pytest.mark.parametrize(
    ("factory", "id", "kwargs"),
    [
        (factories.AdditionalCodeFactory, None, {}),
        (factories.CertificateFactory, "code", {}),
        (factories.FootnoteFactory, None, {}),
        (factories.GeographicalAreaFactory, "area_id", {}),
        (factories.GoodsNomenclatureFactory, "item_id", {}),
        (factories.MeasureFactory, "sid", {"sid": 123456}),
        (factories.QuotaOrderNumberFactory, "order_number", {}),
        (factories.RegulationFactory, "regulation_id", {}),
    ],
)
def test_homepage_search_by_element_id_returns_result(
    factory,
    id,
    kwargs,
    valid_user_client,
):
    model = factory(**kwargs)
    form_data = {
        "search_term": getattr(model, id) if id else model.__str__(),
    }
    response = valid_user_client.post(reverse("home"), form_data)
    assert response.status_code == 302
    assert response.url == model.get_url()


@pytest.mark.parametrize(
    ("name", "expected_url"),
    [
        ("additional codes", "additional_code-ui-list"),
        ("certificates", "certificate-ui-list"),
        ("footnotes", "footnote-ui-list"),
        ("geographical areas", "geo_area-ui-list"),
        ("commodities", "commodity-ui-list"),
        ("measures", "measure-ui-search"),
        ("quotas", "quota-ui-list"),
        ("regulations", "regulation-ui-list"),
    ],
)
def test_homepage_search_by_element_name_returns_result(
    name,
    expected_url,
    valid_user_client,
):
    form_data = {
        "search_term": name,
    }
    response = valid_user_client.post(reverse("home"), form_data)
    assert response.status_code == 302
    assert response.url == reverse(expected_url)


def test_homepage_search_no_result(valid_user_client):
    factories.FootnoteFactory.create()
    response = valid_user_client.post(reverse("home"), {"search_term": "empty"})
    assert response.status_code == 302
    assert response.url == reverse("search-page")


@pytest.mark.parametrize(
    ("heading", "expected_url"),
    [
        ("Application information", reverse_lazy("app-info")),
        ("Importer V1", reverse_lazy("import_batch-ui-list")),
        ("Importer V2", reverse_lazy("taric_parser_import_ui_list")),
        ("TAP reports", reverse_lazy("reports:index")),
        ("Tariff data manual", "https://uktrade.github.io/tariff-data-manual/#home"),
    ],
)
def test_resources_view_displays_resources(heading, expected_url, valid_user_client):
    response = valid_user_client.get(reverse("resources"))
    assert response.status_code == 200

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    assert page.find("h3", string=heading)
    assert page.find("a", href=expected_url)
