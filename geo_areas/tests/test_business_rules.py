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


@pytest.fixture
def dates():
    class Dates:
        normal = DateTimeTZRange(
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 2, 1, tzinfo=timezone.utc),
        )
        earlier = DateTimeTZRange(
            datetime(2019, 1, 1, tzinfo=timezone.utc),
            datetime(2019, 2, 1, tzinfo=timezone.utc),
        )
        later = DateTimeTZRange(
            datetime(2020, 2, 2, tzinfo=timezone.utc),
            datetime(2020, 3, 1, tzinfo=timezone.utc),
        )
        big = DateTimeTZRange(
            datetime(2018, 1, 1, tzinfo=timezone.utc),
            datetime(2022, 1, 2, tzinfo=timezone.utc),
        )
        overlap_normal = DateTimeTZRange(
            datetime(2020, 1, 15, tzinfo=timezone.utc),
            datetime(2020, 2, 15, tzinfo=timezone.utc),
        )
        overlap_big = DateTimeTZRange(
            datetime(2022, 1, 1, tzinfo=timezone.utc),
            datetime(2022, 1, 3, tzinfo=timezone.utc),
        )
        after_big = DateTimeTZRange(
            datetime(2022, 2, 1, tzinfo=timezone.utc),
            datetime(2022, 3, 1, tzinfo=timezone.utc),
        )
        backwards = DateTimeTZRange(
            datetime(2021, 2, 1, tzinfo=timezone.utc),
            datetime(2021, 1, 2, tzinfo=timezone.utc),
        )

    return Dates


def test_ga1(dates):
    """ The combination geographical area id + validity start date must be unique. """
    factories.GeographicalAreaFactory(area_id="AA", valid_between=dates.normal)
    factories.GeographicalAreaFactory(area_id="AB", valid_between=dates.normal)
    factories.GeographicalAreaFactory(area_id="AA", valid_between=dates.later)

    with pytest.raises(IntegrityError):
        factories.GeographicalAreaFactory(area_id="AA", valid_between=dates.normal)


def test_ga2(dates):
    """ The start date must be less than or equal to the end date. """
    with pytest.raises(DataError):
        factories.GeographicalAreaFactory(valid_between=dates.backwards)


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
def test_ga5(dates):
    """ A parent geographical areas validity period must span a childs validity period """
    parent = factories.GeographicalAreaFactory(area_code=1, valid_between=dates.normal)
    with pytest.raises(ValidationError):
        factories.GeographicalAreaFactory(
            area_code=1, valid_between=dates.overlap_normal, parent=parent
        )


@pytest.mark.xfail(reason="GA6 is ignored for now")
def test_ga6(child):
    """ Parent-child relationships cannot loop. """
    grandchild = factories.GeographicalAreaFactory(area_code=1, parent=child)

    with pytest.raises(ValidationError):
        child.parent.parent = grandchild
        child.parent.save()


def test_ga7(dates):
    """ Geographic Areas with the same area id must not overlap. """
    factories.GeographicalAreaFactory(area_id="AA", valid_between=dates.normal)
    with pytest.raises(IntegrityError):
        factories.GeographicalAreaFactory(
            area_id="AA", valid_between=dates.overlap_normal
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

    factories.GeographicalMembershipFactory(member=region, group=group)
    factories.GeographicalMembershipFactory(member=country, group=group)
    with pytest.raises(ValidationError):
        factories.GeographicalMembershipFactory(member=bad_member, group=group)


def test_ga15(dates):
    """ The membership start date must be less than or equal to the membership end date. """
    with pytest.raises(DataError):
        factories.GeographicalMembershipFactory(valid_between=dates.backwards)


def test_ga16_17(dates):
    """ The validity range of the geographical area group must span all membership ranges of its members. """
    group = factories.GeographicalAreaFactory(area_code=1, valid_between=dates.big)

    member = factories.GeographicalAreaFactory(area_code=0, valid_between=dates.normal)
    bad_member = factories.GeographicalAreaFactory(
        area_code=0, valid_between=dates.overlap_big
    )

    factories.GeographicalMembershipFactory(
        group=group, member=member, valid_between=dates.normal
    )
    with pytest.raises(ValidationError):
        factories.GeographicalMembershipFactory(
            group=group, member=bad_member, valid_between=dates.overlap_big
        )


def test_ga18_20(dates):
    """ Multiple memberships between a single area and group must not have overlapping validity ranges. """
    group = factories.GeographicalAreaFactory(area_code=1, valid_between=dates.big)
    member = factories.GeographicalAreaFactory(area_code=0, valid_between=dates.big)

    factories.GeographicalMembershipFactory(
        group=group, member=member, valid_between=dates.normal
    )
    factories.GeographicalMembershipFactory(
        group=group, member=member, valid_between=dates.later
    )
    with pytest.raises(IntegrityError):
        factories.GeographicalMembershipFactory(
            group=group, member=member, valid_between=dates.overlap_normal
        )


def test_ga19(child, country):
    """ If the group has a parent the members must also be members of the parent. """
    member = factories.GeographicalAreaFactory(area_code=0)

    with pytest.raises(ValidationError):
        factories.GeographicalMembershipFactory(group=child, member=member)

    factories.GeographicalMembershipFactory(group=child.parent, member=member)
    factories.GeographicalMembershipFactory(group=child, member=member)


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
