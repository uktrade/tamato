"""Test for browse additional code behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

pytestmark = pytest.mark.django_db


scenarios("features/browse-additional-codes.feature")


@pytest.fixture
@when("I search additional codes with a <search_term>")
def additional_code_search(search_term, client):
    return client.get(reverse("additionalcode-list"), {"search": search_term})


@then("the search result should contain the additional code searched for")
def additional_code_list(additional_code_search):
    results = additional_code_search.json()
    assert len(results) == 1
    result = results[0]
    assert result["code"] == "000"
    assert result["type"]["sid"] == "X"
