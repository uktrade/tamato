"""Common validators."""

import os
from pathlib import Path
from typing import IO
from typing import Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.deconstruct import deconstructible
from werkzeug.utils import secure_filename


@deconstructible
class NumberRangeValidator:
    """Validates a value is a number within a specified (inclusive) range."""

    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value):
        try:
            if not (self.min_value <= value <= self.max_value):
                raise ValidationError(
                    "%(value)s is not between %(min)s and %(max)s.",
                    params={
                        "value": value,
                        "min": self.min_value,
                        "max": self.max_value,
                    },
                )
        except TypeError:
            raise ValidationError(
                "%(value)s is not comparable to %(min)s [%(min_type)s] and %(max)s [%(max_type)s].",
                params={
                    "value": value,
                    "min": self.min_value,
                    "max": self.max_value,
                    "min_type": type(self.min_value),
                    "max_type": type(self.max_value),
                },
            )

    def __eq__(self, other):
        if isinstance(other, NumberRangeValidator):
            return (
                other.min_value == self.min_value and other.max_value == self.max_value
            )
        return False


class NumericSIDValidator(NumberRangeValidator):
    """
    Validates TARIC SID values.

    A TARIC SID is a unique number generated by the system as an internal access
    key. This will be used in areas where there is a need to change access key
    data dynamically, or where the logical key is too long.

    It is commonly a number between 1 and 99999999 (max 8 digits).
    """

    def __init__(self, max_value=99999999):
        super().__init__(1, max_value)


class UpdateType(models.IntegerChoices):
    UPDATE = 1, "Update"
    DELETE = 2, "Delete"
    CREATE = 3, "Create"


class ApplicabilityCode(models.IntegerChoices):
    PERMITTED = 0, "Permitted"
    MANDATORY = 1, "Mandatory"
    NOT_PERMITTED = 2, "Not permitted"


EnvelopeIdValidator = RegexValidator(r"^(?P<year>\d\d)(?P<counter>\d{4})$")

AlphanumericValidator = RegexValidator(
    r"^[0-9A-Za-z\s.',\-]*$",
    ValidationError("Only alphanumeric characters are allowed."),
)
NumericValidator = RegexValidator(
    r"^[0-9]*$",
    ValidationError("Only numbers are allowed."),
)
SymbolValidator = RegexValidator(
    r"^[0-9A-Za-z\s.',()&£$%@!/\+-]*$",
    ValidationError("Only symbols .,/()&£$@!+-% are allowed."),
)


class PasswordPolicyValidator:
    """Validate whether the password contains at least 1 capital letter, 1
    lowercase letter, 1 number and a special character."""

    HELP_TEXT = "Your password must contain at least 1 capital letter, 1 lowercase letter, 1 number and a special character."

    def validate(self, password, user=None):
        if (
            password.isalnum()
            or not any(c.isdigit() for c in password)
            or not any(c.isupper() for c in password)
            or not any(c.islower() for c in password)
        ):
            raise ValidationError(self.HELP_TEXT, code="password_missing_characters")

    def get_help_text(self):
        return self.HELP_TEXT


markdown_tags_allowlist = [
    "h1",
    "h2",
    "h3",
    "em",
    "strong",
    "p",
    "br",
    "blockquote",
    "hr",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tr",
    "th",
    "tbody",
    "td",
]


def validate_filename(filename: str) -> None:
    """
    Validates that `filename` only includes alphanumeric characters and special
    characters such as spaces, hyphens and underscores.

    Raises a `ValidationError` if `filename` includes non-permitted characters.
    """

    # filename might include spaces which secure_filename normalises to underscores
    if filename.replace(" ", "_") != secure_filename(filename):
        raise ValidationError(
            f"File name must only include alphanumeric characters and special characters such as spaces, hyphens and underscores.",
        )


def validate_filepath(source: Union[str, Path, IO], base_path: str = "") -> None:
    """
    Validates that `source` normalises to an absolute path located within
    `base_path` directory (`settings.BASE_DIR` by default).

    Raises a `ValidationError` if the resulting path would be located outside the expected base path.
    """

    if isinstance(source, str):
        path = source
    elif hasattr(source, "name"):
        path = source.name
    else:
        raise ValueError(f"Expected str, Path or File-like object, not {type(source)}")

    if not base_path:
        base_path = settings.BASE_DIR

    full_path = os.path.normpath(os.path.join(base_path, path))
    if not full_path.startswith(base_path):
        raise ValidationError("Invalid file path: {path}")
