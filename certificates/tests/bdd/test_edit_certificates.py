import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

pytestmark = pytest.mark.django_db

scenarios("features/edit.feature")


@pytest.fixture
@when("I edit certificate X000")
def model_edit_page(client_with_current_workbasket, certificate_X000):
    return client_with_current_workbasket.get(certificate_X000.get_url("edit"))


@pytest.fixture
@when("I edit certificate X000")
def model_edit_page_invalid_user(
    client_with_current_workbasket_no_permissions,
    certificate_X000,
):
    return client_with_current_workbasket_no_permissions.get(
        certificate_X000.get_url("edit"),
    )


@then("I am not permitted to edit")
def edit_permission_denied(model_edit_page_invalid_user):
    assert model_edit_page_invalid_user.status_code == 403


@then("I see an edit form")
def edit_permission_granted(model_edit_page):
    assert model_edit_page.status_code == 200


@pytest.fixture
@when("I set the end date before the start date on certificate X000")
def end_date_before_start(client_with_current_workbasket, response, certificate_X000):
    response["response"] = client_with_current_workbasket.post(
        certificate_X000.get_url("edit"),
        {
            "start_date_0": "1",
            "start_date_1": "1",
            "start_date_2": "2021",
            "end_date_0": "1",
            "end_date_1": "1",
            "end_date_2": "1979",
        },
    )
