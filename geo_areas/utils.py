from common.util import date_ranges_overlap
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode


def get_all_members_of_geo_groups(instance, geo_areas):
    all_members = []
    for geo_area in geo_areas:
        if geo_area.area_code == AreaCode.GROUP:
            valid_memberships = [
                member
                for member in GeographicalMembership.objects.filter(
                    geo_group=geo_area,
                )
                if date_ranges_overlap(member.valid_between, instance.valid_between)
            ]
            origins = set(m.member for m in valid_memberships)
            for membership in valid_memberships:
                if membership.member.sid in [m.sid for m in origins]:
                    all_members.append(membership.member)
        else:
            all_members.append(geo_area)

    return all_members
