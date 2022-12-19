import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories

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
