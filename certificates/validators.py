import re

from django.core.validators import RegexValidator

CERTIFICATE_TYPE_SID_REGEX = r"[A-Z0-9]{1}"
certificate_type_sid_validator = RegexValidator(rf"^{CERTIFICATE_TYPE_SID_REGEX}$")

CERTIFICATE_SID_REGEX = r"[A-Z0-9]{3}"
certificate_sid_validator = RegexValidator(rf"^{CERTIFICATE_SID_REGEX}$")

COMBINED_CERTIFICATE_AND_TYPE_ID = re.compile(
    rf"(?P<certificate_type__sid>{CERTIFICATE_TYPE_SID_REGEX})(?P<sid>{CERTIFICATE_SID_REGEX})",
)
