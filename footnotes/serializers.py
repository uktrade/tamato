from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from footnotes import models
from footnotes import validators


@TrackedModelSerializer.register_polymorphic_model
class FootnoteTypeSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    footnote_type_id = serializers.CharField(
        validators=[validators.footnote_type_id_validator]
    )

    class Meta:
        model = models.FootnoteType
        fields = [
            "id",
            "footnote_type_id",
            "application_code",
            "description",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "description_record_code",
            "description_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


class SimpleFootnoteDescriptionSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    class Meta:
        model = models.FootnoteDescription
        fields = [
            "id",
            "description",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class FootnoteSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    footnote_id = serializers.CharField(validators=[validators.footnote_id_validator])
    footnote_type = FootnoteTypeSerializer(required=False)
    descriptions = SimpleFootnoteDescriptionSerializer(many=True, required=False)

    class Meta:
        model = models.Footnote
        fields = [
            "footnote_id",
            "footnote_type",
            "descriptions",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class FootnoteDescriptionSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    described_footnote = FootnoteSerializer(read_only=True)
    description_period_sid = serializers.IntegerField()

    class Meta:
        model = models.FootnoteDescription
        fields = [
            "description_period_sid",
            "described_footnote",
            "description",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "period_record_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]
