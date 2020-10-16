"""
Validators for footnotes
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from common.util import validity_range_contains_range
from common.validators import UpdateType
from workbaskets.validators import WorkflowStatus


# Footnote type application codes
class ApplicationCode(models.IntegerChoices):
    CN_NOMENCLATURE = 1, "CN nomenclature"
    TARIC_NOMENCLATURE = 2, "TARIC nomenclature"
    EXPORT_REFUND_NOMENCLATURE = 3, "Export refund nomenclature"
    WINE_REFERENCE_NOMENCLATURE = 4, "Wine reference nomenclature"
    ADDITIONAL_CODES = 5, "Additional codes"
    CN_MEASURES = 6, "CN measures"
    OTHER_MEASURES = 7, "Other measures"
    MEURSING_HEADING = 8, "Meursing Heading"
    DYNAMIC_FOOTNOTE = 9, "Dynamic footnote"


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

    if footnote.get_descriptions().count() < 1:
        raise ValidationError("At least one description record is mandatory.")


def validate_first_footnote_description_has_footnote_start_date(
    footnote_description,
):
    """FO4"""

    footnote = footnote_description.described_footnote

    if (
        footnote.get_descriptions().count() == 0
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

    if (
        footnote.get_descriptions()
        .filter(valid_between__startswith=footnote_description.valid_between.lower)
        .exists()
    ):
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


def validate_unique_type_and_id(footnote):
    """FO2"""

    # check against active footnotes which are published (or sent to cds?)
    footnotes_with_type_and_id = (
        type(footnote)
        .objects.active()
        .filter(
            workbasket__status=WorkflowStatus.PUBLISHED,
            footnote_id=footnote.footnote_id,
            footnote_type__footnote_type_id=footnote.footnote_type.footnote_type_id,
        )
    )
    if (
        footnote.update_type == UpdateType.CREATE
        and footnotes_with_type_and_id.exists()
    ):
        raise ValidationError("The combination footnote type and code must be unique.")


def validate_footnote_type_validity_includes_footnote_validity(footnote):
    """FO17"""

    if not validity_range_contains_range(
        footnote.footnote_type.valid_between,
        footnote.valid_between,
    ):
        raise ValidationError(
            {
                "valid_between": (
                    "Footnote type validity period must encompass the entire "
                    "footnote validity period"
                ),
            },
        )
