from datetime import date
from typing import Set

from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode


def materialise_geo_area(
    geo_area: GeographicalArea,
    date: date,
    transaction,
) -> Set[GeographicalArea]:
    """Materialise a GeoArea, including its memberships."""
    if geo_area.area_code == AreaCode.GROUP:
        memberships = (
            GeographicalMembership.objects.approved_up_to_transaction(transaction)
            .as_at(date)
            .filter(geo_group__version_group=geo_area.version_group)
        )
        return frozenset(m.member for m in memberships)
    else:
        return frozenset(
            [
                GeographicalArea.objects.approved_up_to_transaction(transaction)
                .as_at(date)
                .get(version_group=geo_area.version_group),
            ],
        )
