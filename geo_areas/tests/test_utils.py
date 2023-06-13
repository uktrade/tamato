import pytest

from common.models.utils import override_current_transaction
from common.tests import factories
from geo_areas.utils import get_all_members_of_geo_groups
from geo_areas.validators import AreaCode

pytestmark = pytest.mark.django_db


def test_get_all_members(date_ranges):
    area_group = factories.GeographicalAreaFactory.create(
        area_code=AreaCode.GROUP,
        valid_between=date_ranges.no_end,
    )
    (
        country1,
        country2,
        country3,
        country4,
    ) = factories.GeographicalAreaFactory.create_batch(
        4,
        area_code=AreaCode.COUNTRY,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country1,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country2,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=area_group,
        member=country3,
        valid_between=date_ranges.no_end,
    )
    area_group2 = factories.GeographicalAreaFactory.create(
        area_code=AreaCode.GROUP,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=area_group2,
        member=country1,
        valid_between=date_ranges.no_end,
    )
    factories.GeographicalMembershipFactory.create(
        geo_group=area_group2,
        member=country2,
        valid_between=date_ranges.no_end,
    )

    origin = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area=area_group,
        valid_between=date_ranges.no_end,
    )

    with override_current_transaction(origin.transaction):
        all_geo_areas = get_all_members_of_geo_groups(origin, [country4, area_group2])

        assert not set(all_geo_areas).difference({country1, country2, country4})
