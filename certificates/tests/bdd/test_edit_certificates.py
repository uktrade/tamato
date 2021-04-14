import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

pytestmark = pytest.mark.django_db

scenarios("features/edit.feature")


@pytest.fixture
@when("I edit certificate X000")
def model_edit_page(client, certificate_X000):
    return client.get(certificate_X000.get_url("edit"))


@then("I am not permitted to edit")
def edit_permission_denied(model_edit_page):
    assert model_edit_page.status_code == 403


@then("I see an edit form")
def edit_permission_granted(model_edit_page):
    assert model_edit_page.status_code == 200
