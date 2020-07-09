from rest_framework import serializers

from additional_codes import models
from additional_codes import validators
from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin


@TrackedModelSerializer.register_polymorphic_model
class AdditionalCodeTypeSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    sid = serializers.CharField(
        validators=[validators.additional_code_type_sid_validator]
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
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    class Meta:
        model = models.AdditionalCodeDescription
        fields = [
            "id",
            "description",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class AdditionalCodeSerializer(ValiditySerializerMixin, TrackedModelSerializerMixin):
    id = serializers.IntegerField()
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


@TrackedModelSerializer.register_polymorphic_model
class AdditionalCodeDescriptionSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    described_additional_code = AdditionalCodeSerializer(read_only=True)

    class Meta:
        model = models.AdditionalCodeDescription
        fields = [
            "id",
            "described_additional_code",
            "description",
            "description_period_sid",
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
