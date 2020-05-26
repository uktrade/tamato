from rest_framework import serializers

from common.serializers import ValiditySerializerMixin
from footnotes import models
from footnotes import validators


class FootnoteTypeDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FootnoteTypeDescription
        fields = ["id", "footnote_type_id", "description"]


class FootnoteTypeSerializer(ValiditySerializerMixin):
    footnote_type_id = serializers.CharField(
        validators=[validators.FootnoteIDValidator]
    )
    descriptions = FootnoteTypeDescriptionSerializer(
        many=True, source="footnotetypedescription_set"
    )

    class Meta:
        model = models.FootnoteType
        fields = ["id", "footnote_type_id", "descriptions", "valid_between"]


class FootnoteDescriptionSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.FootnoteDescription
        fields = ["id", "footnote_id", "description", "valid_between"]


class FootnoteSerializer(ValiditySerializerMixin):
    footnote_id = serializers.CharField(validators=[validators.FootnoteTypeIDValidator])
    footnote_type = FootnoteTypeSerializer()
    descriptions = FootnoteDescriptionSerializer(
        many=True, source="footnotedescription_set"
    )

    class Meta:
        model = models.Footnote
        fields = ["id", "footnote_id", "footnote_type", "descriptions", "valid_between"]
