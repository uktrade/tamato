from rest_framework import serializers

from common.serializers import (
    ValiditySerializerMixin,
    TrackedModelSerializer,
    TrackedModelSerializerMixin,
)
from footnotes import models
from footnotes import validators


class SimpleFootnoteTypeDescriptionSerializer(
    TrackedModelSerializerMixin, serializers.ModelSerializer
):
    class Meta:
        model = models.FootnoteTypeDescription
        fields = [
            "id",
            "footnote_type_id",
            "description",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


@TrackedModelSerializer.register_polymorphic_model
class FootnoteTypeSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    id = serializers.IntegerField()
    footnote_type_id = serializers.CharField(
        validators=[validators.FootnoteIDValidator]
    )
    descriptions = SimpleFootnoteTypeDescriptionSerializer(
        many=True, source="footnotetypedescription_set"
    )

    class Meta:
        model = models.FootnoteType
        fields = [
            "id",
            "footnote_type_id",
            "application_code",
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
class FootnoteTypeDescriptionSerializer(
    TrackedModelSerializerMixin, serializers.ModelSerializer
):
    footnote_type = FootnoteTypeSerializer(read_only=True)

    class Meta:
        model = models.FootnoteTypeDescription
        fields = [
            "id",
            "footnote_type",
            "description",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
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
    id = serializers.IntegerField()
    footnote_id = serializers.CharField(validators=[validators.FootnoteTypeIDValidator])
    footnote_type = FootnoteTypeSerializer()
    descriptions = SimpleFootnoteDescriptionSerializer(
        many=True, source="footnotedescription_set"
    )

    class Meta:
        model = models.Footnote
        fields = [
            "id",
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

    class Meta:
        model = models.FootnoteDescription
        fields = [
            "id",
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
