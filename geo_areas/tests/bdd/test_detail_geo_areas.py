"""Tests for browse geographical area behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when

from geo_areas import models

pytestmark = pytest.mark.django_db


scenarios("features/detail_geo_areas.feature")


@pytest.fixture
@when("I view a geographical_area with id 2222")
def geo_area_detail(client, geographical_area_2222):
    return client.get(geographical_area_2222.get_url())


@pytest.fixture
@when("I view a geographical_area with id 4444")
def geo_area_group_detail(client, geographical_area_4444):
    return client.get(geographical_area_4444.get_url())


@then("the core data of the geographical_area should be presented")
def geo_area_core_data(geo_area_detail, geographical_area_2222):
    content = geo_area_detail.content.decode()

    assert str(geographical_area_2222.area_id) in content
    assert (
        geographical_area_2222.get_description(
            transaction=geographical_area_2222.transaction,
        ).description
        in content
    )
    assert geographical_area_2222.get_area_code_display() in content

    assert f"{geographical_area_2222.valid_between.lower:%d %b %Y}" in content


@then("the descriptions against the geographical_area should be presented")
def geo_area_description_data(geo_area_detail, geographical_area_2222):
    descriptions = geographical_area_2222.descriptions.all()

    content = geo_area_detail.content.decode()

    for description in descriptions:
        assert description.description in content
        assert f"{description.validity_start:%d %b %Y}" in content


def compare_members_to_html(members, html, is_group):
    for member in members:
        obj = member.geo_group if is_group else member.member
        assert f"{member.valid_between.lower:%d %b %Y}" in html
        assert str(obj.area_id) in html
        assert obj.get_description(transaction=obj.transaction).description in html


@then("the memberships against the geographical_area should be presented")
def geo_area_membership_data(geo_area_detail, geographical_area_2222):
    memberships = models.GeographicalMembership.objects.filter(
        member=geographical_area_2222,
    )
    compare_members_to_html(
        memberships,
        geo_area_detail.content.decode(),
        is_group=True,
    )


@then("the members against the geographical_area should be presented")
def geo_area_group_members_data(geo_area_group_detail, geographical_area_4444):
    members = models.GeographicalMembership.objects.filter(
        geo_group=geographical_area_4444,
    )
    compare_members_to_html(
        members,
        geo_area_group_detail.content.decode(),
        is_group=False,
    )
