from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import IntegerChoices
from django.db.models import Subquery

additional_code_type_sid_validator = RegexValidator(r"^[A-Z0-9]$")


class ApplicationCode(IntegerChoices):
    """Code which indicates to which data type an additional code type applies."""

    EXPORT_REFUND_NOMENCLATURE = 0, "Export refund nomenclature"
    ADDITIONAL_CODES = 1, "Additional codes"
    MEURSING_ADDITIONAL_CODES = 3, "Meursing additional codes"
    EXPORT_REFUND_AGRI = 4, "Export refund for processed agricultural goods"


additional_code_validator = RegexValidator(r"^[A-Z0-9][A-Z0-9][A-Z0-9]$")


def validate_at_least_one_description(
    additional_code_class, description_class, workbasket
):
    if not description_class.objects.filter(
        described_additional_code__sid__in=Subquery(
            additional_code_class.objects.filter(workbasket=workbasket).values_list(
                "sid", flat=True
            )
        )
    ).exists():
        raise ValidationError("At least one description record is mandatory.")
