import xml.etree.ElementTree as etree

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories
from common.tests.factories import GoodsNomenclatureFactory
from common.views import DashboardView
from common.views import HealthCheckResponse
from workbaskets.forms import SelectableObjectsForm
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


def test_index_displays_objects_in_current_workbasket(
    valid_user_client,
    workbasket,
):
    """Verify that changes in the current workbasket are displayed on the bulk
    selection form of the index page."""
    with workbasket.new_transaction():
        GoodsNomenclatureFactory.create()

    response = valid_user_client.get(reverse("index"))
    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )
    for obj in workbasket.tracked_models.all():
        field_name = SelectableObjectsForm.field_name_for_object(obj)
        assert page.find("input", {"name": field_name})


def test_index_with_each_type_of_object_in_current_workbasket(
    valid_user_client,
    workbasket,
    trackedmodel_factory,
):
    with workbasket.new_transaction():
        trackedmodel_factory.create()
    response = valid_user_client.get(reverse("index"))
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

    response = valid_user_client.get(reverse("index"))

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

    assert view.latest_upload == None

    factories.UploadFactory.create()
    latest_upload = factories.UploadFactory.create()

    assert view.latest_upload == latest_upload
