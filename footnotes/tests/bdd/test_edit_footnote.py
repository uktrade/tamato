"""Edit Footnote feature tests."""
import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories


pytestmark = pytest.mark.django_db


scenarios("features/edit-footnote.feature")


@given("A current workbasket")
def current_workbasket(client):
    workbasket = factories.WorkBasketFactory()
    session = client.session
    session["workbasket"] = workbasket.to_json()
    session.save()
    return workbasket


@given("Alice has permission to update a footnote")
def alice_has_permission_to_update_a_footnote(footnote_nc000):
    assert alice.has_perm("footnotes.update", footnote_nc000)


@pytest.fixture
@when("I go to edit footnote NC000")
def footnote_edit_screen(client, footnote_nc000):
    return client.get(footnote_nc000.get_url("edit"))


@pytest.fixture
@when("I submit a <change> to footnote NC000")
def i_submit_a_change_to_footnote_nc000(footnote_nc000, change):
    return client.post(footnote_nc000.get_url("edit"), change)


@then("I should be presented with a footnote update screen")
def i_should_be_presented_with_a_footnote_update_screen():
    """I should be presented with a footnote update screen."""
    raise NotImplementedError


@then("I should be presented with a form with the following fields\n{fields}")
def check_fields(fields, footnote_edit_form):
    content = footnote_edit_form.content
    fields = fields.strip().split()
    for field in fields:
        assert field in content


@then("only the start and end date should be editable")
def only_the_start_and_end_date_should_be_editable():
    """only the start and end date should be editable."""
    raise NotImplementedError
