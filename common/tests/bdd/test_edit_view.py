import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

from common.tests import factories

pytestmark = pytest.mark.django_db

scenarios("features")


@pytest.fixture
@given("a model exists")
def tracked_model(approved_transaction):
    return factories.FootnoteFactory.create(
        transaction=approved_transaction,
    )


@pytest.fixture
@when("I edit a model")
def model_edit_page(client_with_current_workbasket, tracked_model):
    return client_with_current_workbasket.get(tracked_model.get_url("edit"))


@pytest.fixture
@when("I edit a model")
def model_edit_page_invalid_user(
    client_with_current_workbasket_no_permissions,
    tracked_model,
):
    return client_with_current_workbasket_no_permissions.get(
        tracked_model.get_url("edit"),
    )


@then("I am not permitted to edit")
def edit_permission_denied(model_edit_page_invalid_user):
    assert model_edit_page_invalid_user.status_code == 403


@then("I see an edit form")
def edit_permission_granted(model_edit_page):
    assert model_edit_page.status_code == 200
