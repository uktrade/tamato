import datetime
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import modify_settings
from django.test import override_settings
from django.urls import reverse
from django.urls import reverse_lazy

from common.tests import factories
from common.util import xml_fromstring
from common.views import HealthCheckView
from common.views import handler403
from common.views import handler500
from tasks.models.task import ProgressState
from tasks.tests.factories import TaskWorkflowFactory

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
    "check_to_mock, mock_result",
    [
        ("common.views.HealthCheckView.check_database", ("OK", 200)),
        ("common.views.HealthCheckView.check_redis_cache", ("OK", 200)),
        ("common.views.HealthCheckView.check_database", ("Not OK", 503)),
        ("common.views.HealthCheckView.check_redis_cache", ("Not OK", 503)),
        ("common.views.HealthCheckView.check_celery_broker", ("Not OK", 503)),
        ("common.views.HealthCheckView.check_s3", ("Not OK", 503)),
    ],
)
@patch(
    "common.views.HealthCheckView.check_celery_broker",
    return_value=("OK", 200),
)
@patch("common.views.HealthCheckView.check_s3", return_value=("OK", 200))
def test_health_check_view_response(
    check_celery_broker_mock,
    check_s3_mock,
    check_to_mock,
    mock_result,
    client,
):
    """Test that `HealthCheckView` returns a Pingdom-compatible HTTP
    response."""
    request = client.get(reverse("healthcheck"))
    view = HealthCheckView()
    with patch(check_to_mock, return_value=mock_result):
        response = view.get(request)
        assert response.status_code == mock_result[1]
        payload = xml_fromstring(response.content)
        assert payload.tag == "pingdom_http_custom_check"
        assert payload[0].tag == "status"
        assert payload[0].text == mock_result[0]
        assert payload[1].tag == "response_time"


def test_app_info_non_superuser(valid_user_client):
    """Users without the superuser permission cannot view the application
    information page."""
    response = valid_user_client.get(reverse("app-info"))

    assert response.status_code == 403


def test_app_info_superuser(superuser_client, new_workbasket):
    """
    Superusers should have an unrestricted view of application information.

    The new_workbasket fixture provides access to transaction information in the
    deployment infomation section.
    """

    sqlite_dumps = [
        {
            "file_name": "123456789.db",
            "file_size": 1000000,
            "created_datetime": datetime.datetime.now(),
        },
    ]

    with patch("common.views.pages.sqlite_dumps", return_value=sqlite_dumps):
        response = superuser_client.get(reverse("app-info"))

    assert response.status_code == 200

    page = BeautifulSoup(str(response.content), "html.parser")
    h2_elements = page.select(".info-section h2")

    assert len(h2_elements) == 4
    assert "Deployment information" in h2_elements[0].text
    assert "Active business rule checks" in h2_elements[1].text
    assert "Active envelope generation tasks" in h2_elements[2].text
    assert "Sqlite dumps (past 30 days)" in h2_elements[3].text


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
        "remove": [
            "authbroker_client.middleware.ProtectAllViewsMiddleware",
            "admin.apps.TamatoAdminConfig",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "common.models.utils.TransactionMiddleware",
            "common.models.utils.ValidateUserWorkBasketMiddleware",
        ],
        "append": "common.middleware.MaintenanceModeMiddleware",
    },
)
def test_user_redirect_during_maintenance_mode(valid_user_client):
    response = valid_user_client.get(reverse("home"))
    assert response.status_code == 302
    assert response.url == reverse("maintenance")

    response = valid_user_client.get(response.url)
    assert response.status_code == 200


def test_maintenance_mode_page_content(valid_user_client):
    response = valid_user_client.get(reverse("maintenance"))
    assert response.status_code == 200
    assert "Sorry, the service is unavailable" in str(response.content)


@pytest.mark.parametrize(
    ("card", "permission"),
    [
        ("Tickets", "view_taskworkflow"),
        ("Workbaskets", "view_workbasket"),
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


def test_homepage_card_tickets(valid_user, valid_user_client):
    ticket1 = TaskWorkflowFactory.create(
        summary_task__progress_state__name=ProgressState.TO_DO,
    )
    ticket2 = TaskWorkflowFactory.create(
        summary_task__progress_state__name=ProgressState.IN_PROGRESS,
    )
    factories.TaskAssigneeFactory.create(user=valid_user, task=ticket1.summary_task)
    factories.TaskAssigneeFactory.create(user=valid_user, task=ticket2.summary_task)

    response = valid_user_client.get(reverse("home"))
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    card = page.find("h3", string="Tickets")
    assert card
    my_tickets = card.find_next("table")
    rows = my_tickets.findChildren(["tr"])
    assert len(rows) == 3
    assert ticket1.title in rows[1].select("td")[1]
    assert "To do" in rows[1].select("td")[2].get_text()
    assert ticket2.title in rows[2].select("td")[1]
    assert "In progress" in rows[2].select("td")[2].get_text()


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


@override_settings(SSO_ENABLED=True)
def test_admin_login_shows_404_when_sso_enabled(superuser_client):
    """Test to check that when staff SSO is enabled, the login page shows a 404
    but the rest of the admin site is still available."""
    response = superuser_client.get(reverse("admin:login"))
    assert response.status_code == 404

    response = superuser_client.get(reverse("admin:index"))
    assert response.status_code == 200
    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    assert page.find("h1", string="Site administration")


@pytest.mark.parametrize(
    "client_name",
    [
        "client",
        "superuser_client",
        "valid_user_client",
    ],
)
def test_tickets_tile_visibility_based_on_user_permissions(client_name, request):
    """This test checks if 'Tickets' tile is only visible to either Tariff
    Managers (valid_user_client used as proxy) or superusers."""
    client = request.getfixturevalue(client_name)
    response = client.get(reverse("home"))

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    card = page.find("h3", string="Tickets")

    if client_name == "client":
        assert not card
    else:
        assert card


@pytest.mark.parametrize(
    "client_name",
    [
        "valid_user_client",
        "superuser_client",
    ],
)
def test_ticket_templates_link_only_visible_to_superuser(client_name, request):
    """This test checks if the 'Ticket Templates' link is only visible to
    superusers."""
    print(f"Using the following client: {client_name}")
    client = request.getfixturevalue(client_name)
    response = client.get(reverse("home"))

    page = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    link_url = reverse("workflow:task-workflow-template-ui-list")
    ticket_templates_link = page.find("a", href=link_url)

    if client_name == "valid_user_client":
        assert not ticket_templates_link
    else:
        assert ticket_templates_link
