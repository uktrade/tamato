from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from psycopg2._range import DateTimeTZRange


AREA_ID_REGEX = r"^[A-Z0-9]{2}$|^[A-Z0-9]{4}$"

area_id_validator = RegexValidator(AREA_ID_REGEX)


class AreaCode(models.IntegerChoices):
    COUNTRY = 0, "Country"
    GROUP = 1, "Geographical Area Group"
    REGION = 2, "Region"


def validity_range_contains_range(
    overall_range: DateTimeTZRange, contained_range: DateTimeTZRange
) -> bool:
    """
    If the contained_range has both an upper and lower bound, check they are both
    within the overall_range.

    If either end is unbounded in the contained range,it must also be unbounded in the overall range.
    """
    if contained_range.upper and contained_range.lower:
        return (
            contained_range.lower in overall_range
            and contained_range.upper in overall_range
        )

    return not (
        (contained_range.upper_inf and overall_range.upper)
        or (contained_range.lower_inf and contained_range.lower)
    )


def validate_description_is_not_null(area_description):
    """
    GA3
    """
    if not area_description.description:
        raise ValidationError({"description": "A description cannot be blank"})


def validate_member_is_country_or_region(area_membership):
    """
    GA13
    """
    if area_membership.member.area_code == AreaCode.GROUP.value:
        raise ValidationError(
            {"area_code": "Group member must be a Country or Region, not a Group"}
        )


def validate_group_is_group(area_membership):
    if area_membership.geo_group.area_code != AreaCode.GROUP.value:
        raise ValidationError(
            {
                "area_code": f"Areas must be a member of a group, not a {area_membership.geo_group.get_area_code_display()}"
            }
        )


def validate_group_validity_includes_membership_validity(area_membership):
    """
    GA16
    """
    group_validity = area_membership.geo_group.valid_between
    membership_validity = area_membership.valid_between

    if not validity_range_contains_range(group_validity, membership_validity):
        raise ValidationError(
            {
                "valid_between": "Group validity period must encompass the entire member validity period"
            }
        )


def validate_members_of_child_group_are_in_parent_group(area_membership):
    """
    GA19
    """
    if not area_membership.geo_group.parent:
        return
    parent = area_membership.geo_group.parent

    if not area_membership.member.groups.filter(geo_group=parent).exists():
        raise ValidationError(
            {
                "group": "Members of a Group, where the Group has a parent Group, "
                "must also be members of the parent Group"
            }
        )
