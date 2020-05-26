"""Tests for browse footnotes behaviours."""
import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories

pytestmark = pytest.mark.django_db


scenarios("features/footnotes.feature")


@given('a valid user named "Alice"')
def valid_user():
    return factories.UserFactory.create(username="Alice")


@given("I am logged in as Alice")
def valid_user_login(client, valid_user):
    client.force_login(valid_user)


@given("footnote NC000")
def footnote_NC000():
    footnote_type = factories.FootnoteTypeFactory(footnote_type_id="NC")
    return factories.FootnoteFactory(footnote_id="000", footnote_type=footnote_type)


@pytest.fixture
@when("I search for a footnote using a footnote ID")
def footnotes_search(client):
    return client.get(reverse("footnote-list"), {"search": "NC000"})


@then("the search result should contain the footnote searched for")
def footnotes_list(footnotes_search):
    results = footnotes_search.json()
    assert len(results) == 1
    result = results[0]
    assert (
        result["footnote_type"]["footnote_type_id"] == "NC"
        and result["footnote_id"] == "000"
    )


@pytest.fixture
@when("I select footnote NC000")
def footnote_details(client, footnote_NC000):
    return client.get(reverse("footnote-detail", kwargs={"pk": footnote_NC000.pk}))


@then("a summary of the core information should be presented")
def footnote_core_data(footnote_details):
    result = footnote_details.json()
    assert {"descriptions", "id", "footnote_id", "valid_between"} <= set(result.keys())
    assert "footnote_type" in result
    assert {"descriptions", "id", "footnote_type_id", "valid_between"} <= set(
        result["footnote_type"].keys()
    )
