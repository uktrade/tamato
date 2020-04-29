"""
Validators for footnotes
"""
import re

from django.core.exceptions import ValidationError


FOOTNOTE_ID = re.compile(r"^([0-9]{3}|[0-9]{5})$")
FOOTNOTE_TYPE_ID = re.compile(r"^([A-Z]{2,3}|[0-9]{2})$")


def valid_footnote_type_id(value):
    if not FOOTNOTE_TYPE_ID.match(value):
        raise ValidationError(
            "A footnote type ID must be 2 or 3 characters A-Z or 2 digits"
        )


def valid_footnote_id(value):
    if not FOOTNOTE_ID.match(value):
        raise ValidationError("A footnote ID must be 3 or 5 digits")
