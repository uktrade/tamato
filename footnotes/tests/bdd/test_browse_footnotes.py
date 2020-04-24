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


@given("some footnotes")
def footnotes():
    return factories.FootnoteFactory.create_batch(10)


@given('a valid user named "Alice"')
def valid_user():
    return factories.UserFactory.create(username="Alice")


@given("I am logged in as Alice")
def valid_user_login(client, valid_user):
    client.force_login(valid_user)


@pytest.fixture
@when("I search for a footnote using a footnote ID")
def footnotes_search(client):
    return client.get(reverse("footnote-list"), {"search": "00000"})


@then("the search result should contain the footnote searched for")
def footnotes_list(footnotes_search):
    results = footnotes_search.json()
    assert len(results) == 1
    assert results[0]["id"] == "00000"
