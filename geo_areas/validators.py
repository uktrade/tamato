from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


AREA_ID_REGEX = r"^[A-Z0-9]{2}$|^[A-Z0-9]{4}$"

area_id_validator = RegexValidator(AREA_ID_REGEX)


class AreaCode(models.IntegerChoices):
    COUNTRY = 0, "Country"
    GROUP = 1, "Geographical Area Group"
    REGION = 2, "Region"


def validate_group_is_group(area_membership):
    if area_membership.geo_group.area_code != AreaCode.GROUP:
        raise ValidationError(
            {
                "area_code": f"Areas must be a member of a group, not a {area_membership.geo_group.get_area_code_display()}"
            }
        )
