from rest_framework import serializers

from common.serializers import ValiditySerializerMixin
from footnotes.models import Footnote
from footnotes.models import FootnoteType


class FootnoteTypeSerializer(ValiditySerializerMixin):
    class Meta:
        model = FootnoteType
        fields = ["id", "application_code", "description", "valid_between"]


class FootnoteSerializer(ValiditySerializerMixin):
    class Meta:
        model = Footnote
        fields = ["id", "footnote_type", "valid_between"]
