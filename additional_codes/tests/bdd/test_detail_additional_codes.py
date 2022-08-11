"""Tests for additional code detail view behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

pytestmark = pytest.mark.django_db


scenarios("features/detail_additional_codes.feature")


@pytest.fixture
@when("I select the additional code X000")
def additional_code_detail(client, additional_code_X000):
    return client.get(
        reverse("additional_code-ui-detail", args=(additional_code_X000.sid,)),
    )


@then("the core data against the additional code should be presented")
def additional_code_core_data(additional_code_detail, additional_code_X000):
    content = additional_code_detail.content.decode()
    ac = additional_code_X000
    act = ac.type

    assert f"{act.sid}{ac.code}" in content
    assert ac.get_description(transaction=ac.transaction).description in content
    assert f"{act.sid} - {act.description}" in content
    assert f"{ac.valid_between.lower:%d %b %Y}" in content


@then("the descriptions against the additional_code should be presented")
def additional_code_description_data(additional_code_detail, additional_code_X000):
    content = additional_code_detail.content.decode()
    ac = additional_code_X000

    for description in ac.descriptions.all():
        assert description.description in content
        assert f"{description.validity_start:%d %b %Y}" in content
