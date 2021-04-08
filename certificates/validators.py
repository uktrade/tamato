from django.core.validators import RegexValidator

CERTIFICATE_TYPE_SID_REGEX = r"^[A-Z0-9]{1}$"
certificate_type_sid_validator = RegexValidator(CERTIFICATE_TYPE_SID_REGEX)

CERTIFICATE_SID_REGEX = r"^[A-Z0-9]{3}$"
certificate_sid_validator = RegexValidator(CERTIFICATE_SID_REGEX)
