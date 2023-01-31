import pytest

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from geo_areas import models

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("membership_data", "expected"),
    (
        (lambda group: [], 0),
        (lambda group: [{"geo_group": group}], 1),
        (lambda group: [{}], 0),
        (lambda group: [{"geo_group": group}, {"geo_group": group}], 2),
    ),
    ids=(
        "no_memberships",
        "membership",
        "member_of_another_group",
        "two_members",
    ),
)
def test_get_current_memberships_on_groups(membership_data, expected):
    group = factories.GeoGroupFactory()
    for data in membership_data(group):
        factories.GeographicalMembershipFactory(**data)

    with override_current_transaction(Transaction.objects.last()):
        assert len(group.get_current_memberships()) == expected


@pytest.mark.parametrize(
    ("membership_data", "expected"),
    (
        (lambda area: [], 0),
        (lambda area: [{"member": area}], 1),
        (lambda area: [{}], 0),
        (lambda area: [{"member": area}, {"member": area}], 2),
    ),
    ids=(
        "no_memberships",
        "membership",
        "group_with_another_member",
        "two_members",
    ),
)
def test_get_current_memberships_on_areas(membership_data, expected):
    area = factories.CountryFactory()
    for data in membership_data(area):
        factories.GeographicalMembershipFactory(**data)

    with override_current_transaction(Transaction.objects.last()):
        assert len(area.get_current_memberships()) == expected


def test_get_current_memberships_when_region_and_country_share_sid():
    country = factories.CountryFactory.create()
    region = factories.RegionFactory.create(sid=country.sid)
    country_membership = factories.GeographicalMembershipFactory.create(member=country)
    region_membership = factories.GeographicalMembershipFactory.create(member=region)
    with override_current_transaction(Transaction.objects.last()):
        country_memberships = country.get_current_memberships()
        region_memberships = region.get_current_memberships()

        assert country_memberships.count() == 2
        assert region_memberships.count() == 2
        assert country_membership in country_memberships
        assert region_membership in country_memberships
        assert country_membership in region_memberships
        assert region_membership in region_memberships


def test_other_on_membership():
    membership = factories.GeographicalMembershipFactory()
    assert membership.other(membership.member) == membership.geo_group
    assert membership.other(membership.geo_group) == membership.member
    with pytest.raises(ValueError):
        membership.other(factories.GeoGroupFactory())
    with pytest.raises(ValueError):
        membership.other(factories.CountryFactory())


def test_other_on_later_version():
    country = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership = factories.GeographicalMembershipFactory.create(
        member=country,
        geo_group=geo_group,
    )
    v2_country = factories.CountryFactory.create(
        sid=country.sid,
        area_code=country.area_code,
    )
    v2_geo_group = factories.GeoGroupFactory.create(sid=geo_group.sid)

    assert membership.other(v2_country) == membership.geo_group
    assert membership.other(v2_geo_group) == membership.member


def test_other_on_same_sid_different_area_code():
    country = factories.CountryFactory.create()
    region = factories.RegionFactory.create(sid=country.sid)
    membership = factories.GeographicalMembershipFactory.create(member=country)

    assert membership.other(region) == membership.geo_group


def test_geo_area_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.GeographicalAreaFactory,
        "in_use",
        factories.MeasureFactory,
        "geographical_area",
    )


@pytest.mark.parametrize(
    "factory",
    [
        factories.GeographicalAreaFactory,
        factories.GeographicalMembershipFactory,
        factories.GeographicalAreaDescriptionFactory,
    ],
)
def test_geo_area_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(factory)


def test_with_latest_description_multiple_version():
    """Tests that, after updating a geo area description,
    with_current_description returns a queryset with one geo area annotated with
    only the latest description."""
    description = factories.GeographicalAreaDescriptionFactory.create(
        description="blarghhh",
    )
    current_description = description.new_version(
        description.transaction.workbasket,
        description="bleurgh",
    )
    with override_current_transaction(current_description.transaction):
        qs = models.GeographicalArea.objects.current().with_latest_description()

        assert qs.count() == 1
        assert qs.first().description == "bleurgh"


def test_with_latest_description_multiple_descriptions(date_ranges):
    """Tests that, where multiple current descriptions exist for an area, the
    description with the latest validity_start date is returned by
    with_latest_description."""
    earlier_description = factories.GeographicalAreaDescriptionFactory.create(
        validity_start=date_ranges.earlier.lower,
    )
    later_description = factories.GeographicalAreaDescriptionFactory.create(
        described_geographicalarea=earlier_description.described_geographicalarea,
        validity_start=date_ranges.later.lower,
    )
    with override_current_transaction(later_description.transaction):
        qs = models.GeographicalArea.objects.current().with_latest_description()

        # sanity check that description objects have been created with different description values
        assert earlier_description.description != later_description.description
        assert qs.first().description == later_description.description


def test_with_current_descriptions(queued_workbasket):
    """Tests that, where multiple current descriptions exist for an area,
    with_current_descriptions returns a queryset annotated with those
    descriptions chained together and separated by a space."""
    description_1 = factories.GeographicalAreaDescriptionFactory.create(
        transaction__workbasket=queued_workbasket,
    )
    description_2 = factories.GeographicalAreaDescriptionFactory.create(
        transaction__workbasket=queued_workbasket,
        described_geographicalarea=description_1.described_geographicalarea,
    )
    with override_current_transaction(description_2.transaction):
        qs = models.GeographicalArea.objects.current().with_current_descriptions()
        area = qs.first()

    # sanity check that description is not an empty string or None
    assert area.description
    assert (
        area.description == f"{description_1.description} {description_2.description}"
    )
