import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories
from publishing.models import ProcessingState

pytestmark = pytest.mark.django_db


def test_empty_queue(valid_user_client):
    response = valid_user_client.get(
        reverse("publishing:envelope-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    assert "no envelopes queued" in page.select("p.govuk-body")[0].text


def test_nonempty_queue(valid_user_client):
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    response = valid_user_client.get(
        reverse("publishing:envelope-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    queued_envelopes_rows = page.select("table.queued-envelopes tbody tr")
    assert len(queued_envelopes_rows) == 2

    process_envelope = page.select("table.queued-envelopes tbody tr .process-envelope")
    assert len(process_envelope) == 1
    assert "Start processing" in process_envelope[0].text


def test_processing_envelope(valid_user_client):
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    # packaged_work_basket.begin_processing()

    # Start processing the workbasket.
    response = valid_user_client.post(
        reverse("publishing:envelope-queue-ui-list"),
        {"process_envelope": f"{packaged_work_basket.pk}"},
    )
    assert response.status_code == 302
    packaged_work_basket.refresh_from_db()
    assert packaged_work_basket.processing_state == ProcessingState.CURRENTLY_PROCESSING

    # Test that the envelope is showing as transitioned in the UI.
    response = valid_user_client.get(
        reverse("publishing:envelope-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    process_envelope = page.select("table.queued-envelopes tbody .process-envelope")
    assert len(process_envelope) == 1
    assert "Download envelope" in process_envelope[0].text
