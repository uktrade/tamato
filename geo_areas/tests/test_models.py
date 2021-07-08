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


def test_other_on_membership():
    membership = factories.GeographicalMembershipFactory()
    assert membership.other(membership.member) == membership.geo_group
    assert membership.other(membership.geo_group) == membership.member
    with pytest.raises(ValueError):
        membership.other(factories.GeoGroupFactory())
    with pytest.raises(ValueError):
        membership.other(factories.CountryFactory())


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
