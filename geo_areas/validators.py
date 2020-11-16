from datetime import datetime
from datetime import timezone

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from common.util import validity_range_contains_range

AREA_ID_REGEX = r"^[A-Z0-9]{2}$|^[A-Z0-9]{4}$"

area_id_validator = RegexValidator(AREA_ID_REGEX)


class AreaCode(models.IntegerChoices):
    COUNTRY = 0, "Country"
    GROUP = 1, "Geographical Area Group"
    REGION = 2, "Region"


def validate_description_is_not_null(area_description):
    """
    GA3
    """
    if area_description.valid_between.lower < datetime(1998, 2, 1, tzinfo=timezone.utc):
        return

    if not area_description.description:
        raise ValidationError({"description": "A description cannot be blank"})


def validate_first_geographical_area_description_has_geographical_area_start_date(
    geographical_area_description,
):
    """GA3"""

    geographical_area = geographical_area_description.area

    if (
        geographical_area.geographicalareadescription_set.count() == 0
        and geographical_area.valid_between.lower
        != geographical_area_description.valid_between.lower
    ):
        raise ValidationError(
            {
                "valid_between": f"The first description for geographical area {geographical_area} "
                f"must have the same start date as the geographical area"
            }
        )


def validate_geographical_area_description_have_unique_start_date(
    geographical_area_description,
):
    """GA3"""
    geographical_area = geographical_area_description.area

    if geographical_area.geographicalareadescription_set.filter(
        valid_between__startswith=geographical_area_description.valid_between.lower
    ).exists():
        raise ValidationError(
            {
                "valid_between": f"Geographical area {geographical_area} cannot have two descriptions with the same start date"
            }
        )


def validate_geographical_area_description_start_date_before_geographical_area_end_date(
    geographical_area_description,
):
    """GA3"""
    geographical_area = geographical_area_description.area

    if (
        geographical_area.valid_between.upper is not None
        and geographical_area_description.valid_between.lower
        >= geographical_area.valid_between.upper
    ):
        raise ValidationError(
            {
                "valid_between": "The start date must be less than or equal to the end "
                "date of the geographical area."
            }
        )


def validate_at_least_one_description(area):
    """
    GA3
    """
    if area.geographicalareadescription_set.count() < 1:
        raise ValidationError("At least one description record is mandatory.")


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
                "valid_between": "Group validity period must encompass the entire member validity period: "
                f"{group_validity} does not encompass {membership_validity}"
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
