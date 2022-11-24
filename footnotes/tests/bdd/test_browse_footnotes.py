"""Tests for browse footnotes behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.models.utils import override_current_transaction

pytestmark = pytest.mark.django_db


scenarios("features/browse-footnotes.feature")


@pytest.fixture
@when("I search for a footnote using a footnote ID")
def footnotes_search(client):
    return client.get(reverse("footnote-list"), {"search": "NC000"})


@then("the search result should contain the footnote searched for")
def footnotes_list(footnotes_search, footnote_NC000):
    results = footnotes_search.json()["results"]
    assert len(results) == 1
    result = results[0]
    with override_current_transaction(footnote_NC000.transaction):
        assert (
            result["label"]
            == f"{footnote_NC000} - {footnote_NC000.get_description().description}"
            and result["value"] == footnote_NC000.pk
        )
