from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup
from django.template.loader import render_to_string

from common.tests.factories import GoodsNomenclatureFactory

pytestmark = pytest.mark.django_db


def test_check_missing_measures_in_progress(user_workbasket):
    user_workbasket.missing_measures_check_task_id = "12345"
    user_workbasket.refresh_from_db()
    mock_request = MagicMock()

    with user_workbasket.new_transaction() as tx:
        GoodsNomenclatureFactory.create(
            transaction=tx,
        )

    rendered = render_to_string(
        "workbaskets/checks/missing_measures.jinja",
        {
            "workbasket": user_workbasket,
            "missing_measures_check_in_progress": True,
            "request": mock_request,
        },
    )
    soup = BeautifulSoup(rendered, "html.parser")
    assert (
        "Missing measures check is in progress. Come back later or refresh to see results"
        in soup.select_one(".govuk-tabs__panel").text
    )
