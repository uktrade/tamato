from rest_framework import serializers

from additional_codes import models
from additional_codes import validators
from common.serializers import ValiditySerializerMixin


class AdditionalCodeTypeSerializer(ValiditySerializerMixin):
    sid = serializers.CharField(
        validators=[validators.additional_code_type_sid_validator]
    )

    class Meta:
        model = models.AdditionalCodeType
        fields = ["id", "sid", "description", "valid_between"]


class AdditionalCodeDescriptionSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.AdditionalCodeDescription
        fields = ["id", "described_additional_code_id", "description", "valid_between"]


class AdditionalCodeSerializer(ValiditySerializerMixin):
    id = serializers.IntegerField()
    sid = serializers.CharField(validators=[validators.additional_code_validator])
    type = AdditionalCodeTypeSerializer()
    descriptions = AdditionalCodeDescriptionSerializer(many=True)

    class Meta:
        model = models.AdditionalCode
        fields = ["id", "sid", "type", "code", "descriptions", "valid_between"]
