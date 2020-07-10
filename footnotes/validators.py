"""
Validators for footnotes
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from common.util import validity_range_contains_range


FOOTNOTE_TYPE_ID_PATTERN = r"[A-Z]{2}[A-Z ]?"
footnote_type_id_validator = RegexValidator(r"^" + FOOTNOTE_TYPE_ID_PATTERN + "$")

FOOTNOTE_ID_PATTERN = r"([0-9]{3}|[0-9]{5})"
footnote_id_validator = RegexValidator(r"^" + FOOTNOTE_ID_PATTERN + "$")


FootnoteIDValidator = None
FootnoteTypeIDValidator = None


# XXX is this in the spec?
def validate_description_is_not_null(obj):
    if not obj.description:
        raise ValidationError({"description": "A description cannot be blank"})


def validate_at_least_one_description(footnote):
    """FO4"""

    if footnote.descriptions.count() < 1:
        raise ValidationError("At least one description record is mandatory.")


def validate_first_footnote_description_has_footnote_start_date(footnote_description,):
    """FO4"""

    footnote = footnote_description.described_footnote

    if (
        footnote.descriptions.count() == 0
        and footnote.valid_between.lower != footnote_description.valid_between.lower
    ):
        raise ValidationError(
            {
                "valid_between": (
                    f"The first description for footnote {footnote} must have "
                    f"the same start date as the footnote"
                ),
            },
        )


def validate_footnote_description_dont_have_same_start_date(footnote_description):
    """FO4"""
    footnote = footnote_description.described_footnote

    if footnote.descriptions.filter(
        valid_between__startswith=footnote_description.valid_between.lower
    ).exists():
        raise ValidationError(
            {
                "valid_between": f"Footnote {footnote} cannot have two descriptions with the same start date"
            }
        )


def validate_footnote_description_start_date_before_footnote_end_date(
    footnote_description,
):
    """FO4"""
    footnote = footnote_description.described_footnote

    if (
        footnote.valid_between.upper is not None
        and footnote_description.valid_between.lower >= footnote.valid_between.upper
    ):
        raise ValidationError(
            {
                "valid_between": (
                    "The start date must be less than or equal to the end date "
                    "of the footnote."
                ),
            },
        )


def validate_footnote_type_validity_includes_footnote_validity(footnote):
    """FO17"""

    type_validity = footnote.footnote_type.valid_between
    footnote_validity = footnote.valid_between

    if not validity_range_contains_range(type_validity, footnote_validity):
        raise ValidationError(
            {
                "valid_between": (
                    "Footnote type validity period must encompass the entire "
                    "footnote validity period"
                ),
            },
        )
