from pytest_bdd import given

from common.tests import factories


@given(
    "geographical_area 2222 with a description and area_code 0",
    target_fixture="geographical_area_2222",
)
def geographical_area_2222():
    area = factories.GeographicalAreaFactory(id=2222, area_id=3333, area_code=0)
    factories.GeographicalAreaDescriptionFactory(
        described_geographicalarea=area,
        description="This is 2222",
    )
    factories.GeographicalAreaDescriptionFactory(
        described_geographicalarea=factories.GeographicalMembershipFactory(
            member=area,
        ).geo_group,
        description="random group description",
    )
    return area


@given(
    "geographical_area 4444 with a description and area_code 1",
    target_fixture="geographical_area_4444",
)
def geographical_area_4444(geographical_area_2222):
    area = factories.GeographicalAreaFactory(id=4444, area_id=5555, area_code=1)
    factories.GeographicalAreaDescriptionFactory(
        described_geographicalarea=area,
        description="This is 4444",
    )
    factories.GeographicalMembershipFactory(
        member=geographical_area_2222,
        geo_group=area,
    )
    return area
