import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
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
def test_GA1(make_duplicate_record):
    """The combination geographical area id + validity start date must be
    unique."""

    duplicate = make_duplicate_record(
        factories.GeographicalAreaFactory,
        identifying_fields=("area_id", "valid_between__lower"),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA1().validate(duplicate)


def test_GA2(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.GeographicalAreaFactory.create(valid_between=date_ranges.backwards)


@only_applicable_after("1998-02-01")
def test_description_not_empty():
    """The area must have a description."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.DescriptionNotEmpty().validate(
            factories.GeographicalAreaDescriptionFactory.create(description=""),
        )


@pytest.mark.xfail(reason="GA3 disabled")
def test_GA3_one_description_mandatory():
    """At least one description record is mandatory."""
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3().validate(
            factories.GeographicalAreaFactory.create(description=None),
        )


def test_GA3_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the geographical_area."""

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3().validate(
            factories.GeographicalAreaFactory.create(
                description__valid_between=date_ranges.later,
            ),
        )


def test_GA3_start_dates_cannot_match():
    """No two associated description periods may have the same start date."""

    existing = factories.GeographicalAreaDescriptionFactory.create()
    factories.GeographicalAreaDescriptionFactory.create(
        area=existing.area,
        valid_between=existing.valid_between,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3().validate(existing.area)


def test_GA3_description_start_before_geographical_area_end(date_ranges):
    """The start date must be less than or equal to the end date of the
    geographical_area."""

    geographical_area = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
        description__valid_between=date_ranges.later,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA3().validate(geographical_area)


def test_GA4():
    """A parent geographical area must be a group."""

    parent = factories.GeographicalAreaFactory.create(area_code=0)

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA4().validate(
            factories.GeographicalAreaFactory.create(area_code=1, parent=parent),
        )


def test_GA5(date_ranges):
    """A parent geographical areas validity period must span a childs validity
    period."""

    parent = factories.GeoGroupFactory.create(valid_between=date_ranges.normal)

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA5().validate(
            factories.GeoGroupFactory.create(
                parent=parent,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_GA6():
    """Parent-child relationships cannot loop."""
    g1 = factories.GeoGroupFactory.create()
    g2 = factories.GeoGroupFactory.create(parent=g1)
    g3 = factories.GeoGroupFactory.create(parent=g2)
    g1.parent = g3
    g1.save(force_write=True)

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA6().validate(g1)


@pytest.mark.xfail(reason="GA7 disabled")
def test_GA7(date_ranges):
    """Geographic Areas with the same area id must not overlap."""

    existing = factories.GeographicalAreaFactory.create(
        valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA7().validate(
            factories.GeographicalAreaFactory.create(
                area_id=existing.area_id,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_GA10(date_ranges):
    """If referenced in a measure the geographical area validity range must span
    the measure validity range."""

    measure = factories.MeasureFactory.create(
        geographical_area__valid_between=date_ranges.starts_with_normal,
        valid_between=date_ranges.normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA10().validate(measure.geographical_area)


def test_GA11(date_ranges):
    """If an area is excluded in a measure then the areas validity must span the
    measure."""

    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area__valid_between=date_ranges.normal,
        modified_measure__valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA11().validate(exclusion.excluded_geographical_area)


def test_GA12(reference_nonexistent_record):
    """The referenced geographical area id (member) must exist."""

    with reference_nonexistent_record(
        factories.GeographicalMembershipFactory,
        "member",
    ) as membership:
        with pytest.raises(BusinessRuleViolation):
            business_rules.GA12().validate(membership)


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

    try:
        business_rules.GA13().validate(
            factories.GeographicalMembershipFactory.create(member__area_code=area_code),
        )
    except BusinessRuleViolation:
        if not expect_error:
            raise
    else:
        if expect_error:
            pytest.fail("DID NOT RAISE BusinessRuleViolation")


def test_GA14(reference_nonexistent_record):
    """The referenced geographical area group id must exist."""

    with reference_nonexistent_record(
        factories.GeographicalMembershipFactory,
        "geo_group",
    ) as membership:
        with pytest.raises(BusinessRuleViolation):
            business_rules.GA14().validate(membership)


def test_GA15(date_ranges):
    """The membership start date must be less than or equal to the membership
    end date."""
    with pytest.raises(DataError):
        factories.GeographicalMembershipFactory.create(
            valid_between=date_ranges.backwards,
        )


def test_GA16(date_ranges):
    """The validity period of the geographical area group must span all
    membership periods of its members."""

    membership = factories.GeographicalMembershipFactory.create(
        geo_group__valid_between=date_ranges.normal,
        member__valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA16().validate(membership)


@pytest.mark.xfail(reason="GA18_20 disabled")
def test_GA17(date_ranges):
    """The validity range of the geographical area group must span all
    membership ranges of its members."""

    membership = factories.GeographicalMembershipFactory.create(
        geo_group__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA17().validate(membership)


def test_GA18(date_ranges):
    """When a geographical area is more than once member of the same group then
    there may be no overlap in their membership periods."""

    existing = factories.GeographicalMembershipFactory.create(
        valid_between=date_ranges.normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA18().validate(
            factories.GeographicalMembershipFactory.create(
                geo_group=existing.geo_group,
                member=existing.member,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_GA19():
    """If the group has a parent the members must also be members of the
    parent."""

    parent = factories.GeoGroupFactory.create()
    child = factories.GeoGroupFactory.create(parent=parent)
    member = factories.CountryFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA19().validate(
            factories.GeographicalMembershipFactory.create(
                geo_group=child,
                member=member,
            ),
        )

    business_rules.GA19().validate(
        factories.GeographicalMembershipFactory.create(geo_group=parent, member=member),
    )

    business_rules.GA19().validate(
        factories.GeographicalMembershipFactory.create(geo_group=child, member=member),
    )


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
    with pytest.raises(BusinessRuleViolation):
        business_rules.GA20().validate(
            factories.GeographicalMembershipFactory.create(
                geo_group=child,
                member=membership.member,
                valid_between=date_ranges.overlap_normal,
            ),
        )


def test_GA21(delete_record):
    """If a geographical area is referenced in a measure then it may not be
    deleted."""

    measure = factories.MeasureFactory.create(
        geographical_area=factories.GeographicalAreaFactory.create(),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA21().validate(delete_record(measure.geographical_area))


def test_GA22(delete_record):
    """A geographical area cannot be deleted if it is referenced as a parent
    geographical area group."""

    child = factories.GeoGroupFactory.create(parent=factories.GeoGroupFactory.create())

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA22().validate(delete_record(child.parent))


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

    with pytest.raises(BusinessRuleViolation):
        business_rules.GA23().validate(delete_record(membership))
