"""
Validators for footnotes
"""
import re

from rest_framework import serializers


FOOTNOTE_ID = re.compile(r"^[A-Z0-9]{3}$")
FOOTNOTE_TYPE_ID = re.compile(r"^[A-Z]{2,3}$")


def valid_footnote_type_id(value):
    if not FOOTNOTE_TYPE_ID.match(value):
        raise serializers.ValidationError(
            "A footnote type ID must be 2 or 3 characters A-Z"
        )


def valid_footnote_id(value):
    if not FOOTNOTE_ID.match(value):
        raise serializers.ValidationError(
            "A footnote ID must be 3 alphanumeric characters"
        )
