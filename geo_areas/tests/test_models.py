import pytest

from common.tests import factories

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

    assert len(area.get_current_memberships()) == expected


def test_get_current_memberships_when_region_and_country_share_sid():
    country = factories.CountryFactory.create()
    region = factories.RegionFactory.create(sid=country.sid)
    country_membership = factories.GeographicalMembershipFactory.create(member=country)
    region_membership = factories.GeographicalMembershipFactory.create(member=region)
    country_memberships = country.get_current_memberships()
    region_memberships = region.get_current_memberships()

    assert country_memberships.count() == 1
    assert country_memberships.first() == country_membership
    assert region_memberships.count() == 1
    assert region_memberships.first() == region_membership
    assert country_memberships != region_memberships


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
