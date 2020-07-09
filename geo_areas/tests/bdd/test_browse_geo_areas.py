"""Tests for browse geographical area behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

pytestmark = pytest.mark.django_db


scenarios("features/browse_geo_areas.feature")


@pytest.fixture
@when("I search for a geographical_area using a <search_term>")
def geo_area_search(search_term, client):
    return client.get(reverse("geoarea-list"), {"search": search_term})


@then("the search result should contain the geographical_area searched for")
def geo_area_list(geo_area_search):
    results = geo_area_search.json()
    assert len(results) == 1
    result = results[0]
    assert result["area_id"] == "1001"
