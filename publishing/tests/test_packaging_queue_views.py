import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories
from publishing.models import OperationalStatus

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
