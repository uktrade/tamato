import xml.etree.ElementTree as etree

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.urls import reverse_lazy

from common.tests import factories
from common.tests.factories import GoodsNomenclatureFactory
from common.views import DashboardView
from common.views import HealthCheckResponse
from workbaskets.forms import SelectableObjectsForm
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_index_displays_workbasket_action_form(valid_user_client):
    response = valid_user_client.get(reverse("index"))

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
            "workbaskets:select-workbasket",
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
    response = client.post(reverse("index"), data)
    assert response.status_code == 302
    assert response.url == reverse(response_url)


def test_dashboard_creates_workbasket_if_needed(valid_user_client, approved_workbasket):
    assert WorkBasket.objects.is_not_approved().count() == 0
    response = valid_user_client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1


def test_dashboard_doesnt_creates_workbasket_if_not_needed(
    valid_user_client,
    new_workbasket,
):
    assert WorkBasket.objects.is_not_approved().count() == 1
    response = valid_user_client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1


def test_dashboard_workbasket_unaffected_by_archived_workbasket(
    valid_user_client,
):
    response = valid_user_client.get(reverse("dashboard"))
    assert response.status_code == 200
    view = response.context_data["view"]
    view_workbasket = view.workbasket

    factories.WorkBasketFactory.create(status=WorkflowStatus.ARCHIVED)
    response = valid_user_client.get(reverse("dashboard"))
    assert response.status_code == 200
    view = response.context_data["view"]
    assert view.workbasket == view_workbasket

    factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    response = valid_user_client.get(reverse("dashboard"))
    assert response.status_code == 200
    view = response.context_data["view"]
    assert view.workbasket == view_workbasket


def test_dashboard_displays_objects_in_current_workbasket(
    valid_user_client,
    workbasket,
):
    """Verify that changes in the current workbasket are displayed on the bulk
    selection form of the index page."""
    with workbasket.new_transaction():
        GoodsNomenclatureFactory.create()

    response = valid_user_client.get(reverse("dashboard"))
    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )
    for obj in workbasket.tracked_models.all():
        field_name = SelectableObjectsForm.field_name_for_object(obj)
        assert page.find("input", {"name": field_name})


def test_dashboard_with_each_type_of_object_in_current_workbasket(
    valid_user_client,
    workbasket,
    trackedmodel_factory,
):
    with workbasket.new_transaction():
        trackedmodel_factory.create()
    response = valid_user_client.get(reverse("dashboard"))
    assert response.status_code == 200


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

    response = valid_user_client.get(reverse("dashboard"))

    assert response.status_code == 200


def test_dashboard_view_uploaded_envelope_dates():
    envelope = factories.EnvelopeFactory.create()
    first_txn = factories.EnvelopeTransactionFactory.create(
        envelope=envelope,
    ).transaction
    last_txn = factories.EnvelopeTransactionFactory.create(
        envelope=envelope,
    ).transaction
    factories.UploadFactory.create(envelope=envelope)
    view = DashboardView()

    assert view.uploaded_envelope_dates["start"] == first_txn.updated_at
    assert view.uploaded_envelope_dates["end"] == last_txn.updated_at


def test_dashboard_view_latest_upload():
    view = DashboardView()

    assert view.latest_upload is None

    factories.UploadFactory.create()
    latest_upload = factories.UploadFactory.create()

    assert view.latest_upload == latest_upload


def test_edit_workbasket_page_sets_workbasket(valid_user_client, workbasket):
    response = valid_user_client.get(
        f"{reverse('workbaskets:edit-workbasket')}?workbasket={workbasket.pk}",
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert workbasket.title in soup.select(".govuk-heading-xl")[0].text
    assert str(workbasket.pk) in soup.select(".govuk-heading-xl")[0].text


@pytest.mark.parametrize(
    "url",
    [
        reverse_lazy("workbaskets:edit-workbasket"),
        reverse_lazy("workbaskets:preview-workbasket"),
        reverse_lazy("workbaskets:review-workbasket"),
    ],
)
def test_workbasket_pages_set_workbasket(url, valid_user_client, workbasket):
    response = valid_user_client.get(
        f"{url}?workbasket={workbasket.pk}",
    )
    assert response.status_code == 200
    assert str(workbasket.id) in str(response.content)


def test_edit_workbasket_page_displays_breadcrumb(valid_user_client, workbasket):
    response = valid_user_client.get(
        f"{reverse('workbaskets:edit-workbasket')}?workbasket={workbasket.pk}&edit=1",
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    breadcrumb_links = [
        element.text for element in soup.select(".govuk-breadcrumbs__link")
    ]
    assert "Edit an existing workbasket" in breadcrumb_links


def test_edit_workbasket_page_hides_breadcrumb(valid_user_client, workbasket):
    response = valid_user_client.get(
        f"{reverse('workbaskets:edit-workbasket')}?workbasket={workbasket.pk}&edit=",
    )
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    breadcrumb_links = [
        element.text for element in soup.select(".govuk-breadcrumbs__link")
    ]
    assert "Edit an existing workbasket" not in breadcrumb_links


def test_edit_workbasket_page_creates_new_workbasket(valid_user_client):
    assert WorkBasket.objects.is_not_approved().count() == 0
    response = valid_user_client.get(reverse("workbaskets:edit-workbasket"))
    assert response.status_code == 200
    assert WorkBasket.objects.is_not_approved().count() == 1


def test_select_workbasket_page_200(valid_user_client):
    factories.WorkBasketFactory.create(status=WorkflowStatus.ARCHIVED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.SENT)
    factories.WorkBasketFactory.create(status=WorkflowStatus.PUBLISHED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    factories.WorkBasketFactory.create(status=WorkflowStatus.APPROVED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.PROPOSED)
    factories.WorkBasketFactory.create(status=WorkflowStatus.ERRORED)
    valid_statuses = {
        WorkflowStatus.EDITING,
        WorkflowStatus.APPROVED,
        WorkflowStatus.PROPOSED,
        WorkflowStatus.ERRORED,
    }
    response = valid_user_client.get(reverse("workbaskets:select-workbasket"))
    assert response.status_code == 200
    soup = BeautifulSoup(str(response.content), "html.parser")
    statuses = [
        element.text for element in soup.select(".govuk-table__row .status-badge")
    ]
    assert len(statuses) == 4
    assert not set(statuses).difference(valid_statuses)
