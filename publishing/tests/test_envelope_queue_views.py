from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories
from publishing.models import PackagedWorkBasket
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


def test_nonempty_queue(valid_user_client, unpause_queue):
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


def test_nonempty_queue_paused(valid_user_client, pause_queue):
    first_packaged_work_basket = factories.PackagedWorkBasketFactory()
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

    # Test that UI correctly shows that the queue is paused.
    process_envelope = page.select(
        "table.queued-envelopes tbody tr .tamato-badge-light-red",
    )
    assert len(process_envelope) == 1

    # Test that attempts to start processing a packaged workbasket fails.
    response = valid_user_client.post(
        reverse("publishing:envelope-queue-ui-list"),
        {"process_envelope": f"{first_packaged_work_basket.pk}"},
    )
    assert response.status_code == 302
    first_packaged_work_basket.refresh_from_db()
    assert (
        first_packaged_work_basket.processing_state
        == ProcessingState.AWAITING_PROCESSING
    )
    assert not PackagedWorkBasket.objects.currently_processing()


def test_processing_envelope(valid_user_client, unpause_queue):
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


def test_accept_envelope(
    mocked_publishing_models_send_emails_delay,
    valid_user_client,
):
    packaged_work_basket = factories.PackagedWorkBasketFactory(
        envelope=factories.EnvelopeFactory(),
    )
    packaged_work_basket.begin_processing()

    accept_view_url = reverse(
        "publishing:accept-envelope-ui-detail",
        kwargs={"pk": packaged_work_basket.pk},
    )
    # Get the form view and ensure it renders correctly.
    response = valid_user_client.get(accept_view_url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    accept_envelope = page.select("h1")
    assert "Accept envelope" in accept_envelope[0].text

    # Submit the form and test the packaged workbasket has transitioned correctly.
    response = valid_user_client.post(
        accept_view_url,
        {"report_file": "", "comments": "Test comments."},
    )
    assert response.status_code == 302
    packaged_work_basket.refresh_from_db()
    assert (
        packaged_work_basket.processing_state == ProcessingState.SUCCESSFULLY_PROCESSED
    )


def test_reject_envelope(
    mocked_publishing_models_send_emails_delay,
    valid_user_client,
):
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_work_basket_1 = factories.PackagedWorkBasketFactory(
            envelope=factories.EnvelopeFactory(),
        )

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_work_basket_2 = factories.PackagedWorkBasketFactory()

    # Demonstrate that packaged workbasket transitions correctly.
    assert packaged_work_basket_1.position == 1
    assert (
        packaged_work_basket_1.processing_state == ProcessingState.AWAITING_PROCESSING
    )
    packaged_work_basket_1.begin_processing()
    packaged_work_basket_1.refresh_from_db()
    assert packaged_work_basket_1.position == 0
    assert (
        packaged_work_basket_1.processing_state == ProcessingState.CURRENTLY_PROCESSING
    )

    # Get the form view and ensure it renders correctly.
    reject_view_url = reverse(
        "publishing:reject-envelope-ui-detail",
        kwargs={"pk": packaged_work_basket_1.pk},
    )
    response = valid_user_client.get(reject_view_url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    reject_envelope = page.select("h1")
    assert "Reject envelope" in reject_envelope[0].text

    # Submit the form and test the queued packaged workbaskets have transitioned
    # correctly.
    response = valid_user_client.post(
        reject_view_url,
        {"report_file": "", "comments": "Test comments."},
    )
    assert response.status_code == 302

    packaged_work_basket_1.refresh_from_db()
    assert packaged_work_basket_1.position == 0
    assert packaged_work_basket_1.processing_state == ProcessingState.FAILED_PROCESSING

    packaged_work_basket_2.refresh_from_db()
    assert packaged_work_basket_2.position == 1
    assert (
        packaged_work_basket_2.processing_state == ProcessingState.AWAITING_PROCESSING
    )
