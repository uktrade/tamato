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


validate_reduction_indicator = NumberRangeValidator(1, 9)

validate_component_sequence_number = NumberRangeValidator(1, 999)
