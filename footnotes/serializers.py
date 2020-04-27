from rest_framework import serializers

from common.serializers import ValiditySerializerMixin
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from footnotes.validators import valid_footnote_id
from footnotes.validators import valid_footnote_type_id


class FootnoteTypeSerializer(ValiditySerializerMixin):
    id = serializers.CharField(
        source="footnote_type_id", validators=[valid_footnote_type_id]
    )

    class Meta:
        model = FootnoteType
        fields = ["id", "description", "valid_between"]


class FootnoteSerializer(ValiditySerializerMixin):
    id = serializers.CharField(source="footnote_id", validators=[valid_footnote_id])
    footnote_type = FootnoteTypeSerializer()

    class Meta:
        model = Footnote
        fields = ["id", "description", "footnote_type", "valid_between"]
