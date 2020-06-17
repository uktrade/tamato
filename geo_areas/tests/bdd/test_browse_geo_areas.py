"""Tests for browse geographical area behaviours."""
import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories

pytestmark = pytest.mark.django_db


scenarios("features/geo_areas.feature")


@given('a valid user named "Alice"')
def valid_user():
    return factories.UserFactory.create(username="Alice")


@given("I am logged in as Alice")
def valid_user_login(client, valid_user):
    client.force_login(valid_user)


@given("geographical_area 1001 with a lorem ipsum description")
def geographical_area_1001():
    area = factories.GeographicalAreaFactory(id=1001)
    factories.GeographicalAreaDescriptionFactory(
        area=area, description="lorem ipsum dolor sit amet"
    )
    return area


@pytest.fixture
@when("I search for a geographical_area using a <search_term>")
def geo_area_search(search_term, client):
    return client.get(reverse("geoarea-list"), {"search": search_term})


@then("the search result should contain the geographical_area searched for")
def geo_area_list(geo_area_search):
    results = geo_area_search.json()
    assert len(results) == 1
    result = results[0]
    assert result["id"] == 1001
