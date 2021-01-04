from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


CERTIFICATE_TYPE_SID_REGEX = r"^[A-Z0-9]{1}$"
certificate_type_sid_validator = RegexValidator(CERTIFICATE_TYPE_SID_REGEX)

CERTIFICATE_SID_REGEX = r"^[A-Z0-9]{3}$"
certificate_sid_validator = RegexValidator(CERTIFICATE_SID_REGEX)


def validate_description_is_not_null(certificate_description):
    if not certificate_description.description:
        raise ValidationError({"description": "A description cannot be blank"})
