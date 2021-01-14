"""Tests for browse footnotes behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

pytestmark = pytest.mark.django_db


scenarios("features/browse-footnotes.feature")


@pytest.fixture
@when("I search for a footnote using a footnote ID")
def footnotes_search(client):
    return client.get(reverse("footnote-list"), {"search": "NC000"})


@then("the search result should contain the footnote searched for")
def footnotes_list(footnotes_search):
    results = footnotes_search.json()["results"]
    assert len(results) == 1
    result = results[0]
    assert (
        result["footnote_type"]["footnote_type_id"] == "NC"
        and result["footnote_id"] == "000"
    )
