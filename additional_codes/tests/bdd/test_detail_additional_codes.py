"""Tests for additional code detail view behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from additional_codes import models


pytestmark = pytest.mark.django_db


scenarios("features/detail_additional_codes.feature")


@pytest.fixture
@when("I select the additional code X000")
def additional_code_detail(client):
    return client.get(reverse("additional_code-ui-detail", args=(1,)))


@then("the core data against the additional code should be presented")
def additional_code_core_data(additional_code_detail, additional_code_X000):
    content = additional_code_detail.content.decode()
    ac = additional_code_X000
    act = ac.type

    assert f"{act.sid}{ac.code}" in content
    assert ac.get_description().description in content
    assert f"{act.sid} - {act.description}" in content
    assert "{:%d %b %Y}".format(ac.valid_between.lower) in content


@then("the descriptions against the additional_code should be presented")
def additional_code_description_data(additional_code_detail, additional_code_X000):
    content = additional_code_detail.content.decode()
    ac = additional_code_X000

    for description in ac.descriptions.all():
        assert description.description in content
        assert "{:%d %b %Y}".format(description.valid_between.lower) in content
