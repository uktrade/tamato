import pytest
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError
from django.db.models import ProtectedError

from common.tests import factories
from common.tests.util import only_applicable_after

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


@only_applicable_after("1998-02-01")
def test_ga3_blanks():
    """ The area must have a description. """
    with pytest.raises(ValidationError):
        factories.GeographicalAreaDescriptionFactory(description="")


def test_ga3_dates(date_ranges):
    """At least one description record is mandatory. The start date of the first
    description period must be equal to the start date of the geographical
    area. Two descriptions may not have the same start date. The start date of the
    description must be less than or equal to the end date of the geographical
    area."""
    with pytest.raises(ValidationError):
        area = factories.GeographicalAreaFactory()
        area.validate_workbasket()

    with pytest.raises(ValidationError):
        factories.GeographicalAreaDescriptionFactory(
            area__valid_between=date_ranges.no_end,
            valid_between=date_ranges.later,
        )

    desc = factories.GeographicalAreaDescriptionFactory()
    with pytest.raises(ValidationError):
        factories.GeographicalAreaDescriptionFactory(
            area=desc.area, valid_between=desc.valid_between
        )

    with pytest.raises(ValidationError):
        factories.GeographicalAreaDescriptionFactory(
            area__valid_between=date_ranges.normal,
            valid_between=date_ranges.later,
        )


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


def test_ga10(date_ranges):
    """If referenced in a measure the geographical area validity range must span the
    measure validity range.
    """

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            geographical_area=factories.GeographicalAreaFactory(
                valid_between=date_ranges.starts_with_normal
            ),
            valid_between=date_ranges.normal,
        )


def test_ga11(date_ranges):
    """If an area is excluded in a measure then the areas validity must span the
    measure.
    """

    membership = factories.GeographicalMembershipFactory(
        member__valid_between=date_ranges.starts_with_normal,
    )

    with pytest.raises(ValidationError):
        factories.MeasureExcludedGeographicalAreaFactory(
            excluded_geographical_area=membership.member,
            modified_measure__geographical_area=membership.geo_group,
            modified_measure__valid_between=date_ranges.normal,
        )


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


def test_ga21(approved_workbasket):
    """If a geographical area is referenced in a measure then it may not be deleted."""

    measure = factories.MeasureFactory(
        geographical_area=factories.GeographicalAreaFactory(),
        workbasket=approved_workbasket,
    )

    with pytest.raises(IntegrityError):
        measure.geographical_area.delete()


def test_ga22(child):
    """ A geographical area cannot be deleted if it is referenced as a parent geographical area group. """
    with pytest.raises(ProtectedError):
        child.parent.delete()


def test_ga23(approved_workbasket):
    """ If a geographical area is excluded in a measure, the area cannot be deleted. """

    membership = factories.GeographicalMembershipFactory()
    exclusion = factories.MeasureExcludedGeographicalAreaFactory(
        excluded_geographical_area=membership.member,
        modified_measure__geographical_area=membership.geo_group,
        workbasket=approved_workbasket,
    )

    with pytest.raises(IntegrityError):
        exclusion.excluded_geographical_area.delete()
