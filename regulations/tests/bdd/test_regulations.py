"""Tests for browse regulations behaviours."""
import pytest
from pytest_bdd import given
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from common.tests import factories

pytestmark = pytest.mark.django_db


scenarios("features/regulations.feature")


@given("some regulations", target_fixture="some_regulations")
def some_regulations():
    return factories.RegulationFactory.create_batch(10)


@given("regulation C2000000", target_fixture="regulation_C2000000")
def regulation_C2000000():
    return factories.RegulationFactory.create(regulation_id="C2000000")


@pytest.fixture
@when("I search for a regulation using a valid Regulation Number")
def regulations_search(client):
    return client.get(reverse("regulation-list"), {"search": "C2000000"})


@then("the search result should contain the regulation searched for")
def regulations_list(regulations_search, regulation_C2000000):
    results = regulations_search.json()["results"]
    assert len(results) == 1
    result = results[0]
    assert (
        result["label"]
        == f"{regulation_C2000000.regulation_id} - {regulation_C2000000.information_text}"
    )
    assert result["value"] == regulation_C2000000.pk


@pytest.fixture
@when("I select regulation C2000000")
def regulation_details(client, regulation_C2000000):
    return client.get(
        reverse(
            "regulation-ui-detail",
            kwargs={
                "role_type": regulation_C2000000.role_type,
                "regulation_id": regulation_C2000000.regulation_id,
            },
        ),
    )


@then("a summary of the core information should be presented")
def regulation_core_data(regulation_details, regulation_C2000000):
    reg = regulation_C2000000
    result = regulation_details.content.decode()
    for value in [
        reg.regulation_id,
        f"{reg.regulation_group.group_id}: {reg.regulation_group.description}",
        reg.information_text,
        reg.public_identifier,
        reg.url,
        f"{reg.valid_between.lower:%d %b %Y}",
        reg.transaction.workbasket.get_status_display(),
    ]:
        assert value in result
