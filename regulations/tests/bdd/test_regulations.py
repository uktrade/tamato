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
def regulations_list(regulations_search):
    results = regulations_search.json()
    assert len(results) == 1
    result = results[0]
    assert result["regulation_id"] == "C2000000"


@pytest.fixture
@when("I select regulation C2000000")
def regulation_details(client, regulation_C2000000):
    return client.get(
        reverse("regulation-detail", kwargs={"pk": regulation_C2000000.pk})
    )


@then("a summary of the core information should be presented")
def regulation_core_data(regulation_details):
    result = regulation_details.json()
    assert {
        "url",
        "role_type",
        "regulation_id",
        "information_text",
        "approved",
        "replacement_indicator",
        "stopped",
        "effective_end_date",
        "community_code",
        "regulation_group",
        "valid_between",
        "amends",
        "amendments",
        "extends",
        "extensions",
        "suspends",
        "suspensions",
        "terminates",
        "terminations",
        "replaces",
        "replacements",
        "subrecord_code",
        "official_journal_page",
        "record_code",
        "published_date",
        "update_type",
        "end_date",
        "start_date",
        "official_journal_number",
    } <= set(result.keys())
