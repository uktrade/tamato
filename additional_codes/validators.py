from django.core.validators import RegexValidator
from django.db.models import IntegerChoices
from django.db.models import TextChoices

additional_code_type_sid_validator = RegexValidator(r"^[A-Z0-9]$")


class ApplicationCode(IntegerChoices):
    """Code which indicates to which data type an additional code type
    applies."""

    EXPORT_REFUND_NOMENCLATURE = 0, "Export refund nomenclature"
    ADDITIONAL_CODES = 1, "Additional codes"
    MEURSING_ADDITIONAL_CODES = 3, "Meursing additional codes"
    EXPORT_REFUND_AGRI = 4, "Export refund for processed agricultural goods"


class TypeChoices(TextChoices):
    """SID choices for Additional Code Types."""

    TARIFF_PREFERENCE = "2", "2 - Tariff preference"
    PROHIBITION = "3", "3 - Prohibition / Restriction / Surveillance"
    RESTRICTIONS = "4", "4 - Restrictions"
    AGRICULTURAL_TABLES = "6", "6 - Agricultural Tables (non-Meursing)"
    ANTI_DUMPING_8 = "8", "8 - Anti-dumping / countervailing"
    EXPORT_REFUNDS = "9", "9 - Export Refunds"
    ANTI_DUMPING_A = "A", "A - Anti-dumping / countervailing"
    ANTI_DUMPING_B = "B", "B - Anti-dumping / countervailing"
    ANTI_DUMPING_C = "C", "C - Anti-dumping / countervailing"
    DUAL_USE = "D", "D - Dual Use"
    REFUND = "P", "P - Refund for basic products"
    TRADE_REMEDIES = (
        "T",
        "T - This is the additional code type for UK trade remedies from 2021",
    )
    VAT = "V", "V - VAT"
    EXCISE = "X", "X - EXCISE"


additional_code_validator = RegexValidator(r"^[A-Z0-9][A-Z0-9][A-Z0-9]$")
