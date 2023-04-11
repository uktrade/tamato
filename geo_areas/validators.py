from django.core.validators import RegexValidator
from django.db import models

AREA_ID_REGEX = r"^[A-Z0-9]{2}$|^[A-Z0-9]{4}$"

area_id_validator = RegexValidator(AREA_ID_REGEX)


class AreaCode(models.IntegerChoices):
    COUNTRY = 0, "Country"
    GROUP = 1, "Geographical Area Group"
    REGION = 2, "Region"


def validate_dates(
    form,
    field,
    start_date=None,
    end_date=None,
    group_start_date=None,
    group_end_date=None,
):
    """
    Adds an error message to a form field if a start and end date is not within
    a Geographical Area Group's start and end date.

    Used by forms in GeographicalAreaEditForm for creating and updating
    Geographical Memberships.
    """

    if end_date and start_date and end_date < start_date:
        form.add_error(
            field,
            "The end date must be the same as or after the start date.",
        )

    if start_date and group_start_date and start_date < group_start_date:
        form.add_error(
            field,
            "The start date must be the same as or after the area group's start date.",
        )

    if start_date and group_end_date and start_date > group_end_date:
        form.add_error(
            field,
            "The start date must be the same as or before the area group's end date.",
        )

    if end_date and group_start_date and end_date < group_start_date:
        form.add_error(
            field,
            "The end date must be the same as or after the area group's start date.",
        )

    if group_end_date:
        if end_date and end_date > group_end_date or not end_date:
            form.add_error(
                field,
                "The end date must be the same as or before the area group's end date.",
            )
