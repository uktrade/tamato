from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from checks.tests.factories import MissingMeasureCommCodeFactory
from checks.tests.factories import MissingMeasuresCheckFactory
from common.tests.factories import GoodsNomenclatureFactory

pytestmark = pytest.mark.django_db


def test_check_missing_measures_200(valid_user_client, user_workbasket):
    url = reverse("workbaskets:workbasket-ui-missing-measures-check")
    response = valid_user_client.get(url)
    assert response.status_code == 200


def test_check_missing_measures_fail_list(valid_user_client, user_workbasket):

    with user_workbasket.new_transaction() as tx:
        GoodsNomenclatureFactory.create(
            transaction=tx,
        )

    missing_measures_check = MissingMeasuresCheckFactory.create(
        workbasket=user_workbasket,
        successful=False,
        hash=user_workbasket.commodity_measure_changes_hash,
    )
    MissingMeasureCommCodeFactory.create_batch(
        3,
        missing_measures_check=missing_measures_check,
    )
    url = reverse("workbaskets:workbasket-ui-missing-measures-check")
    response = valid_user_client.get(url)
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert (
        "The following commodity codes are missing a 103 measure type:"
        in soup.select_one(".govuk-tabs__panel").text
    )
    assert len(soup.select("tbody .govuk-table__row")) == 3


def test_check_missing_measures_success(valid_user_client, user_workbasket):
    with user_workbasket.new_transaction() as tx:
        GoodsNomenclatureFactory.create(
            transaction=tx,
        )
    MissingMeasuresCheckFactory.create(
        workbasket=user_workbasket,
        successful=True,
    )
    url = reverse("workbaskets:workbasket-ui-missing-measures-check")
    response = valid_user_client.get(url)
    soup = BeautifulSoup(str(response.content), "html.parser")
    assert (
        "There are no missing 103 measures."
        in soup.select_one(".govuk-tabs__panel").text
    )


@patch("workbaskets.views.ui.WorkBasketCommCodeChecks.run_missing_measures_check")
def test_check_missing_measures_start(
    mock_start_check,
    valid_user_client,
    user_workbasket,
):
    url = reverse("workbaskets:workbasket-ui-missing-measures-check")
    data = {"form-action": "start-check"}
    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    assert response.url == url
    mock_start_check.assert_called_once()


@patch("workbaskets.models.WorkBasket.terminate_missing_measures_check")
def test_check_missing_measures_stop(
    mock_stop_check,
    valid_user_client,
    user_workbasket,
):
    url = reverse("workbaskets:workbasket-ui-missing-measures-check")
    data = {"form-action": "stop-check"}
    response = valid_user_client.post(url, data)
    assert response.status_code == 302
    assert response.url == url
    mock_stop_check.assert_called_once()
