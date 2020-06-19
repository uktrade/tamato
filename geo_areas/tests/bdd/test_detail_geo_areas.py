"""Tests for browse geographical area behaviours."""
import pytest
from pytest_bdd import scenarios
from pytest_bdd import then
from pytest_bdd import when
from rest_framework.reverse import reverse

from geo_areas import models

pytestmark = pytest.mark.django_db


scenarios("features/detail_geo_areas.feature")


@pytest.fixture
@when("I view a geographical_area with id 1001")
def geo_area_detail(client):
    return client.get(reverse("geoarea-ui-detail", args=(1001,)))


@pytest.fixture
@when("I view a geographical_area with id 1002")
def geo_area_group_detail(client):
    return client.get(reverse("geoarea-ui-detail", args=(1002,)))


@then("the core data of the geographical_area should be presented")
def geo_area_core_data(geo_area_detail, geographical_area_1001):
    content = geo_area_detail.content.decode()

    assert str(geographical_area_1001.sid) in content
    assert geographical_area_1001.get_description().description in content
    assert (
        f"{geographical_area_1001.area_code} - {geographical_area_1001.get_area_code_display()}"
        in content
    )

    assert "{:%d %b %Y}".format(geographical_area_1001.valid_between.lower) in content


@then("the descriptions against the geographical_area should be presented")
def geo_area_description_data(geo_area_detail, geographical_area_1001):
    descriptions = geographical_area_1001.geographicalareadescription_set.all()

    content = geo_area_detail.content.decode()

    for description in descriptions:
        assert description.description in content
        assert "{:%d %b %Y}".format(description.valid_between.lower) in content


def compare_members_to_html(members, html, is_group):
    for member in members:
        obj = member.geo_group if is_group else member.member
        assert "{:%d %b %Y}".format(member.valid_between.lower) in html
        assert str(obj.sid) in html
        assert obj.get_description().description in html


@then("the memberships against the geographical_area should be presented")
def geo_area_membership_data(geo_area_detail, geographical_area_1001):
    memberships = models.GeographicalMembership.objects.filter(
        member=geographical_area_1001
    )
    compare_members_to_html(
        memberships, geo_area_detail.content.decode(), is_group=True
    )


@then("the members against the geographical_area should be presented")
def geo_area_group_members_data(geo_area_group_detail, geographical_area_1002):
    members = models.GeographicalMembership.objects.filter(
        geo_group=geographical_area_1002
    )
    compare_members_to_html(
        members, geo_area_group_detail.content.decode(), is_group=False
    )
