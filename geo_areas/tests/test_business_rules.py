from datetime import datetime, timezone

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, DataError
from django.db.models import ProtectedError
from psycopg2.extras import DateTimeTZRange

from common.tests import factories


pytestmark = pytest.mark.django_db


@pytest.fixture
def group():
    return factories.GeographicalAreaFactory(area_code=1)


@pytest.fixture
def country():
    return factories.GeographicalAreaFactory(area_code=0)


@pytest.fixture
def region():
    return factories.GeographicalAreaFactory(area_code=2)


@pytest.fixture()
def child(group):
    return factories.GeographicalAreaFactory(area_code=1, parent=group)


def test_ga1(date_ranges):
    """ The combination geographical area id + validity start date must be unique. """
    factories.GeographicalAreaFactory(area_id="AA", valid_between=date_ranges.normal)
    factories.GeographicalAreaFactory(area_id="AB", valid_between=date_ranges.normal)
    factories.GeographicalAreaFactory(area_id="AA", valid_between=date_ranges.later)

    with pytest.raises(IntegrityError):
        factories.GeographicalAreaFactory(
            area_id="AA", valid_between=date_ranges.normal
        )


def test_ga2(date_ranges):
    """ The start date must be less than or equal to the end date. """
    with pytest.raises(DataError):
        factories.GeographicalAreaFactory(valid_between=date_ranges.backwards)


def test_ga3():
    """ The area must have a description. """
    with pytest.raises(ValidationError):
        factories.GeographicalAreaDescriptionFactory(description="")


@pytest.mark.xfail(reason="GA4 is ignored for now")
def test_ga4():
    """ A parent geographical area must be a group. """
    parent = factories.GeographicalAreaFactory(area_code=0)

    with pytest.raises(ValidationError):
        factories.GeographicalAreaFactory(area_code=1, parent=parent)


@pytest.mark.xfail(reason="GA5 is ignored for now")
def test_ga5(date_ranges):
    """ A parent geographical areas validity period must span a childs validity period """
    parent = factories.GeographicalAreaFactory(
        area_code=1, valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.GeographicalAreaFactory(
            area_code=1, valid_between=date_ranges.overlap_normal, parent=parent
        )


@pytest.mark.xfail(reason="GA6 is ignored for now")
def test_ga6(child):
    """ Parent-child relationships cannot loop. """
    grandchild = factories.GeographicalAreaFactory(area_code=1, parent=child)

    with pytest.raises(ValidationError):
        child.parent.parent = grandchild
        child.parent.save()


def test_ga7(date_ranges):
    """ Geographic Areas with the same area id must not overlap. """
    factories.GeographicalAreaFactory(area_id="AA", valid_between=date_ranges.normal)
    with pytest.raises(IntegrityError):
        factories.GeographicalAreaFactory(
            area_id="AA", valid_between=date_ranges.overlap_normal
        )


@pytest.mark.skip(reason="Measures not yet implemented")
def test_ga10():
    """ If referenced in a measure the geographical area validity range must span the measured validity range. """
    pass


@pytest.mark.skip(reason="Measures not yet implemented")
def test_ga11():
    """ If an area is excluded in a measure then the areas validity must span the measures. """
    pass


def test_ga13(group, region, country):
    """ The referenced geographical area id (member) can only be linked to a country or region. """
    bad_member = factories.GeographicalAreaFactory(area_code=1)

    factories.GeographicalMembershipFactory(member=region, geo_group=group)
    factories.GeographicalMembershipFactory(member=country, geo_group=group)
    with pytest.raises(ValidationError):
        factories.GeographicalMembershipFactory(member=bad_member, geo_group=group)


def test_ga15(date_ranges):
    """ The membership start date must be less than or equal to the membership end date. """
    with pytest.raises(DataError):
        factories.GeographicalMembershipFactory(valid_between=date_ranges.backwards)


def test_ga16_17(date_ranges):
    """ The validity range of the geographical area group must span all membership ranges of its members. """
    group = factories.GeographicalAreaFactory(
        area_code=1, valid_between=date_ranges.big
    )

    member = factories.GeographicalAreaFactory(
        area_code=0, valid_between=date_ranges.normal
    )
    bad_member = factories.GeographicalAreaFactory(
        area_code=0, valid_between=date_ranges.overlap_big
    )

    factories.GeographicalMembershipFactory(
        geo_group=group, member=member, valid_between=date_ranges.normal
    )
    with pytest.raises(ValidationError):
        factories.GeographicalMembershipFactory(
            geo_group=group, member=bad_member, valid_between=date_ranges.overlap_big
        )


def test_ga18_20(date_ranges):
    """ Multiple memberships between a single area and group must not have overlapping validity ranges. """
    group = factories.GeographicalAreaFactory(
        area_code=1, valid_between=date_ranges.big
    )
    member = factories.GeographicalAreaFactory(
        area_code=0, valid_between=date_ranges.big
    )

    factories.GeographicalMembershipFactory(
        geo_group=group, member=member, valid_between=date_ranges.normal
    )
    factories.GeographicalMembershipFactory(
        geo_group=group, member=member, valid_between=date_ranges.later
    )
    with pytest.raises(IntegrityError):
        factories.GeographicalMembershipFactory(
            geo_group=group, member=member, valid_between=date_ranges.overlap_normal
        )


def test_ga19(child, country):
    """ If the group has a parent the members must also be members of the parent. """
    member = factories.GeographicalAreaFactory(area_code=0)

    with pytest.raises(ValidationError):
        factories.GeographicalMembershipFactory(geo_group=child, member=member)

    factories.GeographicalMembershipFactory(geo_group=child.parent, member=member)
    factories.GeographicalMembershipFactory(geo_group=child, member=member)


@pytest.mark.skip(reason="Measures not yet implemented")
def test_ga21():
    """ If a geographical area is referenced in a measure then it may not be deleted1. """
    pass


def test_ga22(child):
    """ A geographical area cannot be deleted if it is referenced as a parent geographical area group. """
    with pytest.raises(ProtectedError):
        child.parent.delete()


@pytest.mark.skip(reason="Measures not yet implemented")
def test_ga23():
    """ If a geographical area is excluded in a measure, the area cannot be deleted. """
    pass
