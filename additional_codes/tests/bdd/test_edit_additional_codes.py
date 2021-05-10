from datetime import date
from datetime import timedelta

import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

from common.tests.util import validity_period_post_data

pytestmark = pytest.mark.django_db

scenarios("features/edit_additional_codes.feature")


@pytest.fixture
@when("I edit additional code X000")
def model_edit_page(client, additional_code_X000):
    return client.get(additional_code_X000.get_url("edit"))


@then("I am not permitted to edit")
def edit_permission_denied(model_edit_page):
    assert model_edit_page.status_code == 403


@then("I see an edit form")
def edit_permission_granted(model_edit_page):
    assert model_edit_page.status_code == 200


@pytest.fixture
@when("I set the end date before the start date on additional code X000")
def end_date_before_start(client, response, additional_code_X000):
    response["response"] = client.post(
        additional_code_X000.get_url("edit"),
        validity_period_post_data(
            start=date(2021, 1, 1),
            end=date(1979, 1, 1),
        ),
    )


@when(
    "I set the start date of additional code X000 to overlap the previous additional code",
)
def submit_overlapping(client, response, additional_code_X000, old_additional_code):
    response["response"] = client.post(
        additional_code_X000.get_url("edit"),
        validity_period_post_data(
            start=old_additional_code.valid_between.lower,
            end=old_additional_code.valid_between.upper + timedelta(days=1),
        ),
    )
