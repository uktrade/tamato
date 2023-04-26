from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

ITEM_ID_REGEX = r"\d{10}"
item_id_validator = RegexValidator(ITEM_ID_REGEX)

SUFFIX_REGEX = r"\d{2}"
suffix_validator = RegexValidator(SUFFIX_REGEX)


def validate_file_type(file):
    if file.content_type != "text/xml":
        raise ValidationError(
            f"File format not supported",
        )
