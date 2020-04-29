from rest_framework import serializers

from common.serializers import ValiditySerializerMixin
from footnotes import models
from footnotes import validators


class FootnoteTypeSerializer(ValiditySerializerMixin):
    id = serializers.CharField(
        source="footnote_type_id", validators=[validators.valid_footnote_type_id]
    )

    class Meta:
        model = models.FootnoteType
        fields = ["id", "description", "valid_between"]


class FootnoteSerializer(ValiditySerializerMixin):
    id = serializers.CharField(
        source="footnote_id", validators=[validators.valid_footnote_id]
    )
    footnote_type = FootnoteTypeSerializer()

    class Meta:
        model = models.Footnote
        fields = ["id", "description", "footnote_type", "valid_between"]
