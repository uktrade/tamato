from pytest_bdd import given

from common.tests import factories


@given(
    "geographical_area 1001 with a description and area_code 0",
    target_fixture="geographical_area_1001",
)
def geographical_area_1001():
    area = factories.GeographicalAreaFactory(id=1001, area_id=1001, area_code=0)
    factories.GeographicalAreaDescriptionFactory(
        described_geographicalarea=area,
        description="This is 1001",
    )
    factories.GeographicalAreaDescriptionFactory(
        described_geographicalarea=factories.GeographicalMembershipFactory(
            member=area,
        ).geo_group,
        description="random group description",
    )
    return area


@given(
    "geographical_area 1002 with a description and area_code 1",
    target_fixture="geographical_area_1002",
)
def geographical_area_1002(geographical_area_1001):
    area = factories.GeographicalAreaFactory(id=1002, area_id=1002, area_code=1)
    factories.GeographicalAreaDescriptionFactory(
        described_geographicalarea=area,
        description="This is 1002",
    )
    factories.GeographicalMembershipFactory(
        member=geographical_area_1001,
        geo_group=area,
    )
    return area
