"""Edit Footnote feature tests."""
from datetime import date
from datetime import timedelta

import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

from common.tests.util import validity_period_post_data

pytestmark = pytest.mark.django_db


scenarios("features/edit-footnote.feature")


@pytest.fixture
@when("I edit footnote NC000")
def footnote_edit_screen(client, footnote_NC000):
    return client.get(footnote_NC000.get_url("edit"))


@then("I see an edit form")
def edit_permission_granted(footnote_edit_screen):
    assert footnote_edit_screen.status_code == 200


@pytest.fixture
@when("I set the end date before the start date on footnote NC000")
def end_date_before_start(client, response, footnote_NC000):
    response["response"] = client.post(
        footnote_NC000.get_url("edit"),
        validity_period_post_data(
            start=date(2021, 1, 1),
            end=date(1979, 1, 1),
        ),
    )


@when("I set the start date of footnote NC000 to predate the footnote type")
def submit_predating(client, response, footnote_NC000):
    response["response"] = client.post(
        footnote_NC000.get_url("edit"),
        validity_period_post_data(
            start=footnote_NC000.footnote_type.valid_between.lower - timedelta(days=1),
            end=footnote_NC000.valid_between.upper,
        ),
    )
