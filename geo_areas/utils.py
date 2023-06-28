from common.util import date_ranges_overlap
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode


def get_all_members_of_geo_groups(validity, geo_areas):
    all_members = set()
    for geo_area in geo_areas:
        if geo_area.area_code == AreaCode.GROUP:
            all_members.update(
                {
                    membership.member
                    for membership in GeographicalMembership.objects.filter(
                        geo_group=geo_area,
                    )
                    .current()
                    .prefetch_related("member")
                    if date_ranges_overlap(membership.valid_between, validity)
                },
            )
        else:
            all_members.add(geo_area)

    return all_members
