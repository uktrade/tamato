from unittest.mock import MagicMock
from unittest.mock import patch

import factory
import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from publishing.models import ProcessingState

pytestmark = pytest.mark.django_db


def test_empty_queue(valid_user_client):
    response = valid_user_client.get(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    assert "no workbasket" in page.select("p.govuk-body")[0].text


def test_nonempty_queue(valid_user_client):
    factories.PackagedWorkBasketFactory()
    factories.PackagedWorkBasketFactory()

    response = valid_user_client.get(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    packaged_work_baskets_rows = page.select("table.packaged-workbaskets tbody tr")
    assert len(packaged_work_baskets_rows) == 2


def test_cds_downloaded(valid_user_client):
    packaged_work_basket = factories.PackagedWorkBasketFactory()
    packaged_work_basket.begin_processing()

    response = valid_user_client.get(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    processing_state = page.select("table.packaged-workbaskets tbody .processing-state")
    assert len(processing_state) == 1
    assert "CDS DOWNLOADED" in processing_state[0].text


def test_unpause_queue(valid_user_client, pause_queue):
    """Unpause the queue and ensure UI and system state correctly reflect
    that."""

    assert OperationalStatus.is_queue_paused()

    response = valid_user_client.post(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
        {"unpause_queue": "unpause_queue"},
    )
    assert response.status_code == 302
    assert not OperationalStatus.is_queue_paused()

    response = valid_user_client.get(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    pause_button = page.select(".pause-queue-button")
    assert len(pause_button) == 1


def test_pause_queue(valid_user_client, unpause_queue):
    """Pause the queue and ensure UI and system state correctly reflect that."""

    assert not OperationalStatus.is_queue_paused()

    response = valid_user_client.post(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
        {"pause_queue": "pause_queue"},
    )
    assert response.status_code == 302
    assert OperationalStatus.is_queue_paused()

    response = valid_user_client.get(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
    )
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    unpause_button = page.select(".unpause-queue-button")
    assert len(unpause_button) == 1


def test_remove_from_queue(valid_user_client):
    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_work_basket_1 = factories.PackagedWorkBasketFactory()

    with patch(
        "publishing.tasks.create_xml_envelope_file.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ):
        packaged_work_basket_2 = factories.PackagedWorkBasketFactory()

    assert PackagedWorkBasket.objects.all_queued().count() == 2
    assert packaged_work_basket_1.position == 1
    assert (
        packaged_work_basket_1.processing_state == ProcessingState.AWAITING_PROCESSING
    )
    assert packaged_work_basket_2.position == 2
    assert (
        packaged_work_basket_2.processing_state == ProcessingState.AWAITING_PROCESSING
    )

    response = valid_user_client.post(
        reverse("publishing:packaged-workbasket-queue-ui-list"),
        {"remove_from_queue": packaged_work_basket_1.pk},
    )
    assert response.status_code == 302

    packaged_work_basket_1.refresh_from_db()
    packaged_work_basket_2.refresh_from_db()

    assert PackagedWorkBasket.objects.all_queued().count() == 1
    assert packaged_work_basket_1.position == 0
    assert packaged_work_basket_1.processing_state == ProcessingState.ABANDONED
    assert packaged_work_basket_2.position == 1
    assert (
        packaged_work_basket_2.processing_state == ProcessingState.AWAITING_PROCESSING
    )
