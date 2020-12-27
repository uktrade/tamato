from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import IntegerChoices

from common.util import validity_range_contains_range

additional_code_type_sid_validator = RegexValidator(r"^[A-Z0-9]$")


class ApplicationCode(IntegerChoices):
    """Code which indicates to which data type an additional code type applies."""

    EXPORT_REFUND_NOMENCLATURE = 0, "Export refund nomenclature"
    ADDITIONAL_CODES = 1, "Additional codes"
    MEURSING_ADDITIONAL_CODES = 3, "Meursing additional codes"
    EXPORT_REFUND_AGRI = 4, "Export refund for processed agricultural goods"


def application_code_validator(value):
    if value not in ApplicationCode.values:
        raise ValidationError(
            "%(value)s is not a valid application code.", params={"value": value}
        )


additional_code_validator = RegexValidator(r"^[A-Z0-9][A-Z0-9][A-Z0-9]$")


def validate_description_is_not_null(obj):
    if not obj.description:
        raise ValidationError({"description": "A description cannot be blank"})


def validate_additional_code_type(obj):
    """ACN2

    The referenced additional code type must exist and have as application code
    "non-Meursing" or "Export refund for processed agricultural good".
    """
    try:
        if obj.type is None:
            return
    except ObjectDoesNotExist as e:
        raise ValidationError("The referenced additional code type must exist.") from e

    permitted_codes = [
        ApplicationCode.ADDITIONAL_CODES,
        ApplicationCode.EXPORT_REFUND_AGRI,
    ]
    if obj.type.application_code not in [
        app_code.value for app_code in permitted_codes
    ]:
        permitted = " or ".join(f'"{app_code.label}"' for app_code in permitted_codes)
        raise ValidationError(
            {
                "type": f"The additional code type application code must be one of {permitted}",
            }
        )


def validate_additional_code_type_validity_includes_additional_code_validity(
    additional_code,
):
    """ACN17"""

    type_validity = additional_code.type.valid_between
    additional_code_validity = additional_code.valid_between

    if not validity_range_contains_range(type_validity, additional_code_validity):
        raise ValidationError(
            {
                "valid_between": "Additional code type validity period must encompass "
                "the entire additional code validity period"
            }
        )


def validate_first_additional_code_description_has_additional_code_start_date(
    additional_code_description,
):
    """ACN5"""

    additional_code = additional_code_description.described_additional_code

    if (
        additional_code.descriptions.count() == 0
        and additional_code.valid_between.lower
        != additional_code_description.valid_between.lower
    ):
        raise ValidationError(
            {
                "valid_between": f"The first description for additional code {additional_code} "
                f"must have the same start date as the additional code"
            }
        )


def validate_additional_code_description_dont_have_same_start_date(
    additional_code_description,
):
    """ACN5"""
    additional_code = additional_code_description.described_additional_code

    if additional_code.descriptions.filter(
        valid_between__startswith=additional_code_description.valid_between.lower
    ).exists():
        raise ValidationError(
            {
                "valid_between": f"Additional code {additional_code} cannot have two descriptions with the same start date"
            }
        )


def validate_additional_code_description_start_date_before_additional_code_end_date(
    additional_code_description,
):
    """ACN5"""
    additional_code = additional_code_description.described_additional_code

    if (
        additional_code.valid_between.upper is not None
        and additional_code_description.valid_between.lower
        > additional_code.valid_between.upper
    ):
        raise ValidationError(
            {
                "valid_between": "The start date must be less than or equal to the end "
                "date of the additional code."
            }
        )


def validate_at_least_one_description(additional_code):
    if additional_code.descriptions.count() < 1:
        raise ValidationError("At least one description record is mandatory.")
