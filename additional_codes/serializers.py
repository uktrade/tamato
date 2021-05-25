from rest_framework import serializers

from additional_codes import models
from additional_codes import validators
from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.serializers import ValidityStartSerializerMixin


@TrackedModelSerializer.register_polymorphic_model
class AdditionalCodeTypeSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    sid = serializers.CharField(
        validators=[validators.additional_code_type_sid_validator],
    )

    class Meta:
        model = models.AdditionalCodeType
        fields = [
            "id",
            "sid",
            "description",
            "application_code",
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


class SimpleAdditionalCodeDescriptionSerializer(
    ValidityStartSerializerMixin,
    TrackedModelSerializerMixin,
):
    class Meta:
        model = models.AdditionalCodeDescription
        fields = [
            "id",
            "description",
            "start_date",
            "validity_start",
        ]


@TrackedModelSerializer.register_polymorphic_model
class AdditionalCodeSerializer(ValiditySerializerMixin, TrackedModelSerializerMixin):
    sid = serializers.CharField(validators=[validators.additional_code_validator])
    type = AdditionalCodeTypeSerializer()
    descriptions = SimpleAdditionalCodeDescriptionSerializer(many=True)

    class Meta:
        model = models.AdditionalCode
        fields = [
            "id",
            "sid",
            "type",
            "code",
            "descriptions",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


class AdditionalCodeImporterSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    sid = serializers.IntegerField()
    type = AdditionalCodeTypeSerializer(required=False)

    class Meta:
        model = models.AdditionalCode
        fields = [
            "sid",
            "type",
            "code",
            "valid_between",
            "update_type",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class AdditionalCodeDescriptionSerializer(
    ValidityStartSerializerMixin,
    TrackedModelSerializerMixin,
):
    described_additionalcode = AdditionalCodeSerializer(read_only=True)

    class Meta:
        model = models.AdditionalCodeDescription
        fields = [
            "described_additionalcode",
            "description",
            "validity_start",
            "sid",
            "update_type",
            "record_code",
            "subrecord_code",
            "period_record_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
        ]


class AdditionalCodeDescriptionImporterSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    described_additionalcode = AdditionalCodeSerializer(required=False)
    sid = serializers.IntegerField()

    class Meta:
        model = models.AdditionalCodeDescription
        fields = [
            "described_additionalcode",
            "description",
            "sid",
            "validity_start",
            "update_type",
            "start_date",
        ]
