import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
from common.tests.util import raises_if
from geo_areas import business_rules
from geo_areas.validators import AreaCode

pytestmark = pytest.mark.django_db


@pytest.fixture()
def child():
    return factories.GeographicalAreaFactory.create(
        area_code=1,
        parent=factories.GeoGroupFactory.create(),
    )


@pytest.mark.xfail(reason="GA1 disabled")
def test_GA1(assert_handles_duplicates):
    """The combination geographical area id + validity start date must be
    unique."""

    assert_handles_duplicates(
        factories.GeographicalAreaFactory,
        business_rules.GA1,
        identifying_fields=("area_id", "valid_between__lower"),
    )


def test_GA2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.GeographicalAreaFactory.create(valid_between=date_ranges.backwards)


@only_applicable_after("1998-02-01")
def test_description_not_empty():
    """The area must have a description."""
    description = factories.GeographicalAreaDescriptionFactory.create(description="")
    with pytest.raises(BusinessRuleViolation):
        business_rules.DescriptionNotEmpty(description.transaction).validate(
            description,
        )


@pytest.mark.xfail(reason="GA3 disabled")
def test_GA3_one_description_mandatory():
    """At least one description record is mandatory."""
    area = factories.GeographicalAreaFactory.create(description=None)
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3(area.transaction).validate(area)


def test_GA3_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the geographical_area."""
    area = factories.GeographicalAreaFactory.create(
        description__validity_start=date_ranges.later.lower,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3(area.transaction).validate(area)


def test_GA3_start_dates_cannot_match():
    """No two associated description periods may have the same start date."""

    existing = factories.GeographicalAreaDescriptionFactory.create()
    duplicate = factories.GeographicalAreaDescriptionFactory.create(
        described_geographicalarea=existing.described_geographicalarea,
        validity_start=existing.validity_start,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3(duplicate.transaction).validate(
            existing.described_geographicalarea,
        )


def test_GA3_description_start_before_geographical_area_end(date_ranges):
    """The start date must be less than or equal to the end date of the
    geographical_area."""

    geographical_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
        description__validity_start=date_ranges.later.lower,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3(geographical_area.transaction).validate(geographical_area)


def test_GA4():
    """A parent geographical area must be a group."""

    parent = factories.GeographicalAreaFactory.create(area_code=0)
    child = factories.GeographicalAreaFactory.create(area_code=1, parent=parent)
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA4(child.transaction).validate(child)


def test_GA5(assert_spanning_enforced):
    """A parent geographical areas validity period must span a childs validity
    period."""

    assert_spanning_enforced(
        factories.GeoGroupFactory,
        business_rules.GA5,
        has_parent=True,
    )


def test_GA6():
    """Parent-child relationships cannot loop."""
    g1 = factories.GeoGroupFactory.create()
    g2 = factories.GeoGroupFactory.create(parent=g1)
    g3 = factories.GeoGroupFactory.create(parent=g2)
    g1.parent = g3
    g1.save(force_write=True)

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA6(g3.transaction).validate(g1)


@pytest.mark.xfail(reason="GA7 disabled")
def test_GA7(date_ranges):
    """Geographic Areas with the same area id must not overlap."""

    existing = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )
    duplicate = factories.GeographicalAreaFactory.create(
        area_id=existing.area_id,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA7(duplicate.transaction).validate(duplicate)


def test_GA10(assert_spanning_enforced):
    """If referenced in a measure the geographical area validity range must span
    the measure validity range."""

    assert_spanning_enforced(
        factories.GeographicalAreaFactory,
        business_rules.GA10,
        measures=factories.related_factory(
            factories.MeasureFactory,
            factory_related_name="geographical_area",
        ),
    )


def test_GA11(assert_spanning_enforced):
    """If an area is excluded in a measure then the areas validity must span the
    measure."""

    assert_spanning_enforced(
        factories.GeographicalAreaFactory,
        business_rules.GA11,
        measureexcludedgeographicalarea=factories.related_factory(
            factories.MeasureExcludedGeographicalAreaFactory,
            factory_related_name="excluded_geographical_area",
        ),
    )


def test_GA12(reference_nonexistent_record):
    """The referenced geographical area id (member) must exist."""

    with reference_nonexistent_record(
        factories.GeographicalMembershipFactory,
        "member",
    ) as membership:
        with pytest.raises(BusinessRuleViolation):
            business_rules.GA12(membership.transaction).validate(membership)


@pytest.mark.parametrize(
    "area_code, expect_error",
    [
        (AreaCode.COUNTRY, False),
        (AreaCode.GROUP, True),
        (AreaCode.REGION, False),
    ],
    ids=["country", "group", "region"],
)
def test_GA13(area_code, expect_error):
    """The referenced geographical area id (member) can only be linked to a
    country or region."""
    membership = factories.GeographicalMembershipFactory.create(
        member__area_code=area_code,
    )

    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.GA13(membership.transaction).validate(membership)


def test_GA14(reference_nonexistent_record):
    """The referenced geographical area group id must exist."""

    with reference_nonexistent_record(
        factories.GeographicalMembershipFactory,
        "geo_group",
    ) as membership:
        with pytest.raises(BusinessRuleViolation):
            business_rules.GA14(membership.transaction).validate(membership)


def test_GA15(date_ranges):
    """The membership start date must be less than or equal to the membership
    end date."""
    with pytest.raises(DataError):
        factories.GeographicalMembershipFactory.create(
            valid_between=date_ranges.backwards,
        )


def test_GA16(assert_spanning_enforced):
    """The validity period of the geographical area group must span all
    membership periods of its members."""

    assert_spanning_enforced(
        factories.GeographicalMembershipFactory,
        business_rules.GA16,
    )


def test_GA17(assert_spanning_enforced):
    """The validity range of the geographical area group must span all
    membership ranges of its members."""

    assert_spanning_enforced(
        factories.GeographicalMembershipFactory,
        business_rules.GA17,
    )


def test_GA18(date_ranges):
    """When a geographical area is more than once member of the same group then
    there may be no overlap in their membership periods."""

    existing = factories.GeographicalMembershipFactory.create(
        valid_between=date_ranges.normal,
    )
    duplicate = factories.GeographicalMembershipFactory.create(
        geo_group=existing.geo_group,
        member=existing.member,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA18(duplicate.transaction).validate(duplicate)


# https://uktrade.atlassian.net/browse/TP2000-469
def test_GA18_multiple_versions(date_ranges):
    """Test that GA18 fires for overlapping memberships when one membership is
    created with a later version of the member area."""
    existing = factories.GeographicalMembershipFactory.create(
        valid_between=date_ranges.normal,
    )
    new_version_member = existing.member.new_version(existing.transaction.workbasket)
    duplicate = factories.GeographicalMembershipFactory.create(
        geo_group=existing.geo_group,
        member=new_version_member,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA18(duplicate.transaction).validate(duplicate)


def test_GA19():
    """If the group has a parent the members must also be members of the
    parent."""

    parent = factories.GeoGroupFactory.create()
    child = factories.GeoGroupFactory.create(parent=parent)
    member = factories.CountryFactory.create()
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=child,
        member=member,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA19(membership.transaction).validate(membership)

    membership = factories.GeographicalMembershipFactory.create(
        geo_group=parent,
        member=member,
    )
    business_rules.GA19(membership.transaction).validate(membership)

    membership = factories.GeographicalMembershipFactory.create(
        geo_group=child,
        member=member,
    )
    business_rules.GA19(membership.transaction).validate(membership)


def test_GA20(date_ranges):
    """If the associated geographical area group has a parent geographical area
    group then the membership period of each member of the parent group must
    span the membership period of the same geographical area in the geographical
    area group."""

    parent = factories.GeoGroupFactory.create()
    child = factories.GeoGroupFactory.create(parent=parent)
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=parent,
        valid_between=date_ranges.normal,
    )
    recursive_membership = factories.GeographicalMembershipFactory.create(
        geo_group=child,
        member=membership.member,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA20(recursive_membership.transaction).validate(
            recursive_membership,
        )


def test_GA21(delete_record):
    """If a geographical area is referenced in a measure then it may not be
    deleted."""

    measure = factories.MeasureFactory.create(
        geographical_area=factories.GeographicalAreaFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA21(measure.transaction).validate(
            delete_record(measure.geographical_area),
        )


def test_GA22(delete_record):
    """A geographical area cannot be deleted if it is referenced as a parent
    geographical area group."""

    child = factories.GeoGroupFactory.create(parent=factories.GeoGroupFactory.create())
    deleted = delete_record(child.parent)
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA22(deleted.transaction).validate(deleted)


def test_GA23(delete_record):
    """If a geographical area is referenced as an excluded geographical area in
    a measure, the membership association with the measure geographical area
    group cannot be deleted."""

    measure = factories.MeasureFactory.create(
        geographical_area=factories.GeoGroupFactory.create(),
    )
    membership = factories.GeographicalMembershipFactory.create(
        geo_group=measure.geographical_area,
    )
    factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership.member,
    )
    deleted = delete_record(membership)
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA23(deleted.transaction).validate(deleted)
