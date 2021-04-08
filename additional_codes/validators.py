from django.core.validators import RegexValidator
from django.db.models import IntegerChoices

additional_code_type_sid_validator = RegexValidator(r"^[A-Z0-9]$")


class ApplicationCode(IntegerChoices):
    """Code which indicates to which data type an additional code type
    applies."""

    EXPORT_REFUND_NOMENCLATURE = 0, "Export refund nomenclature"
    ADDITIONAL_CODES = 1, "Additional codes"
    MEURSING_ADDITIONAL_CODES = 3, "Meursing additional codes"
    EXPORT_REFUND_AGRI = 4, "Export refund for processed agricultural goods"


additional_code_validator = RegexValidator(r"^[A-Z0-9][A-Z0-9][A-Z0-9]$")
