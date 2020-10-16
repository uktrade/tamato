"""Edit Footnote feature tests."""
import re

import pytest
from dateutil.relativedelta import relativedelta
from pytest_bdd import given
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories


pytestmark = pytest.mark.django_db


scenarios("features/edit-footnote.feature")


@given("a current workbasket")
def current_workbasket(client):
    workbasket = factories.WorkBasketFactory()
    session = client.session
    session["workbasket"] = workbasket.to_json()
    session.save()
    return workbasket


@pytest.fixture
@when("I go to edit footnote NC000")
def footnote_edit_screen(client, footnote_NC000):
    return client.get(footnote_NC000.get_url("edit"))


@pytest.fixture
@when("I submit a <change> to footnote NC000")
def submit_footnote_NC000(client, footnote_NC000, change):
    existing = footnote_NC000.valid_between

    def make_payload(lower=None, upper=None):
        payload = {}
        if lower:
            payload.update(
                valid_between_0_0=lower.day,
                valid_between_0_1=lower.month,
                valid_between_0_2=lower.year,
            )
        if upper:
            payload.update(
                valid_between_1_0=upper.day,
                valid_between_1_1=upper.month,
                valid_between_1_2=upper.year,
            )
        return payload

    change_payload = {
        "start date": make_payload(existing.lower + relativedelta(days=+1)),
        "end date": make_payload(
            existing.lower, existing.upper + relativedelta(months=+1)
        ),
    }
    return client.post(footnote_NC000.get_url("edit"), change_payload[change])


@then("I should be presented with a footnote update screen")
def i_should_be_presented_with_a_footnote_update_screen(
    submit_footnote_NC000, footnote_NC000
):
    """I should be presented with a footnote update screen."""
    assert submit_footnote_NC000.status_code == 302
    assert submit_footnote_NC000.url.endswith("/confirm-update/")


@then("I should be presented with a form with an <enabled> <field> field")
def check_fields(enabled, field, footnote_edit_screen):
    content = footnote_edit_screen.content.decode()
    matches = re.findall(r'<[^>]*id="' + field + r'"[^>]*>', content)
    assert matches
    if enabled == "disabled":
        assert "disabled" in matches[0]
