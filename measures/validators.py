import logging

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from parsec import ParseError

from common.validators import ApplicabilityCode  # noqa: simplifies import in models
from common.validators import NumberRangeValidator

measure_type_series_id_validator = RegexValidator(r"^[A-Z][A-Z ]?$")
measurement_unit_code_validator = RegexValidator(r"^[A-Z0-9]{3}$")
measurement_unit_qualifier_code_validator = RegexValidator(r"^[A-Z]$")
monetary_unit_code_validator = RegexValidator(r"^[A-Z]{3}$")
measure_type_id_validator = RegexValidator(r"^[0-9]{3}|[0-9]{6}|[A-Z]{3}$")
measure_condition_code_validator = RegexValidator(r"^[A-Z][A-Z ]?$")

logger = logging.getLogger(__name__)


# XXX even though we can't add to or modify these, shouldn't they live in the DB?
class DutyExpressionId(models.IntegerChoices):
    """
    Duty expression IDs control how the duty amount is interpreted. Multiple
    duty expressions are concatenated in ID order, which is why multiple IDs
    have the same meaning.

    The following values (and their descriptions) are the only possible values
    without having a major impact on HMRC systems.
    """

    DE1 = 1, "% or amount"
    DE2 = 2, "minus % or amount"
    DE3 = 3, "The rate is replaced by the levy"
    DE4 = 4, "+ % or amount"
    DE5 = 5, "The rate is replaced by the reduced levy"
    DE6 = 6, "+ Suplementary amount"
    DE7 = 7, "+ Levy"
    DE9 = 9, "+ Reduced levy"
    DE11 = 11, "+ Variable component"
    DE12 = 12, "+ agricultural component"
    DE13 = 13, "+ Reduced variable component"
    DE14 = 14, "+ reduced agricultural component"
    DE15 = 15, "Minimum"
    DE17 = 17, "Maximum"
    DE19 = 19, "+ % or amount"
    DE20 = 20, "+ % or amount"
    DE21 = 21, "+ additional duty on sugar"
    DE23 = 23, "+ 2 % Additional duty on sugar"
    DE25 = 25, "+ reduced additional duty on sugar"
    DE27 = 27, "+ additional duty on flour"
    DE29 = 29, "+ reduced additional duty on flour"
    DE31 = 31, "Accession compensatory amount"
    DE33 = 33, "+ Accession compensatory amount"
    DE35 = 35, "Maximum"
    DE36 = 36, "minus % CIF"
    DE37 = 37, "(nothing)"
    DE40 = 40, "Export refunds for cereals"
    DE41 = 41, "Export refunds for rice"
    DE42 = 42, "Export refunds for eggs"
    DE43 = 43, "Export refunds for sugar"
    DE44 = 44, "Export refunds for milk products"
    DE99 = 99, "Supplementary unit"


class MeasureTypeCombination(models.IntegerChoices):
    SINGLE_MEASURE = 0, "Only 1 measure at export and 1 at import from the series"
    ALL_MEASURES = 1, "All measure types in the series to be considered"


class MeasureExplosionLevel(models.IntegerChoices):
    HARMONISED_SYSTEM_CHAPTER = 2, "Harmonised System Chapter"
    HARMONISED_SYSTEM_HEADING = 4, "Harmonised System Heading"
    HARMONISED_SYSTEM_SUBHEADING = 6, "Harmonised System Subheading"
    COMBINED_NOMENCLATURE = 8, "Combined Nomenclature"
    TARIC = 10, "TARIC"


class ImportExportCode(models.IntegerChoices):
    IMPORT = 0, "Import"
    EXPORT = 1, "Export"
    BOTH = 2, "Import/Export"


validate_priority_code = NumberRangeValidator(1, 9)


class OrderNumberCaptureCode(models.IntegerChoices):
    MANDATORY = 1, "Mandatory"
    NOT_PERMITTED = 2, "Not permitted"


def validate_measure_explosion_level(value):
    if value not in MeasureExplosionLevel.values:
        raise ValidationError(
            f"Explosion level must be one of {MeasureExplosionLevel.values}",
        )


def validate_action_code(value):
    try:
        index = int(value)
    except ValueError as e:
        raise ValidationError(f"Action code must be a number") from e

    NumberRangeValidator(1, 999)(index)


def validate_duties(duties, measure_start_date):
    """Validate duty sentence by parsing it."""
    from measures.parsers import DutySentenceParser

    duty_sentence_parser = DutySentenceParser.get(
        measure_start_date,
    )

    try:
        duty_sentence_parser.parse(duties)
    except ParseError as e:
        # More helpful errors could be emitted here -
        # for example if an amount or currency is missing
        # it may be possible to highlight that.
        logger.error("Error parse duty sentence %s", e)
        raise ValidationError("Enter a valid duty sentence.")


def validate_conditions_formset(cleaned_data):
    """
    Checks condition formset level errors using set checks:

    Checks that all certficates are unique for the same condition code Checks
    that all referenced prices are unique for the same condition code Checks
    that all action codes for the same condition code are equal Checks that all
    condition codes are entered in the correct order
    """
    errors_list = []
    # list of tuples of condition code and certification
    condition_certificates = []
    # list of tuples of condition code and duty amount data
    condition_duty_amounts = []
    # list of condition codes
    condition_codes = []
    # list of condition code tuples containing conditions & True/False depending on if it's a positive negative action
    condition_negative_action_bool = []
    # list of tuples of condition code and it's action code
    condition_action_tuple = []
    for condition in cleaned_data:
        if condition["duty_amount"]:
            condition_duty_amounts.append(
                (
                    condition["condition_code"],
                    condition["duty_amount"],
                    condition["monetary_unit"],
                    condition["condition_measurement"],
                ),
            )
        if condition["required_certificate"]:
            condition_certificates.append(
                (condition["condition_code"], condition["required_certificate"]),
            )

        condition_negative_action_bool.append(
            (
                condition["condition_code"],
                not (
                    bool(condition["reference_price"])
                    | bool(condition["required_certificate"])
                    | bool(condition["applicable_duty"])
                ),
            ),
        )
        condition_action_tuple.append(
            (condition["condition_code"], condition["action"]),
        )
        condition_codes.append(condition["condition_code"])

    num_unique_certificates = len(set(condition_certificates))
    num_unique_duty_amounts = len(set(condition_duty_amounts))
    num_unique_condition_action_codes = len(set(condition_action_tuple))
    num_unique_condition_negative_action_bool = len(set(condition_negative_action_bool))
    ordered_condition_codes = sorted(condition_codes)

    # for the number of certificates the number of unique certificate, condition code tuples
    # must be equal if the form is valid. Ie/ there are no duplicate certiicates for a condition code
    if len(condition_certificates) != num_unique_certificates:
        errors_list.append(
            ValidationError(
                "The same certificate cannot be added more than once to the same condition code.",
            ),
        )
    if len(condition_duty_amounts) != num_unique_duty_amounts:
        errors_list.append(
            ValidationError(
                "The same price cannot be added more than once to the same condition code.",
            ),
        )

    # for all unique condition codes the number of unique action codes will be equal
    # if the form is valid
    if num_unique_condition_negative_action_bool != num_unique_condition_action_codes:
        errors_list.append(
            ValidationError(
                "All conditions of the same condition code must have the same resulting action.",
            ),
        )

    # Condition codes must be added in order
    if condition_codes != ordered_condition_codes:
        errors_list.append(
            ValidationError(
                "All conditions codes must be added in alphabetical order.",
            ),
        )
    if errors_list:
        raise ValidationError(errors_list)


validate_reduction_indicator = NumberRangeValidator(1, 9)

validate_component_sequence_number = NumberRangeValidator(1, 999)
