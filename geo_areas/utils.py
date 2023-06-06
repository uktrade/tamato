from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode


def get_all_members_of_geo_groups(instance, geo_areas):
    valid_memberships = GeographicalMembership.objects.as_at(
        instance.valid_between.lower,
    )

    all_exclusions = []
    for exclusion in geo_areas:
        if exclusion.area_code == AreaCode.GROUP:
            measure_origins = set(
                m.member
                for m in valid_memberships.filter(
                    geo_group=instance.geographical_area,
                )
            )
            for membership in valid_memberships.filter(geo_group=exclusion):
                if membership.member.sid in [m.sid for m in measure_origins]:
                    all_exclusions.append(membership.member)
        else:
            all_exclusions.append(exclusion)

    return set(all_exclusions)
