from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from measures import models
from measures import validators


@TrackedModelSerializer.register_polymorphic_model
class MeasurementUnitSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    code = serializers.CharField(
        validators=[validators.measurement_unit_code_validator],
    )

    class Meta:
        model = models.MeasurementUnit
        fields = [
            "code",
            "description",
            "valid_between",
            "update_type",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class MeasurementUnitQualifierSerializer(
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
):
    code = serializers.CharField(
        validators=[validators.measurement_unit_qualifier_code_validator],
    )

    class Meta:
        model = models.MeasurementUnitQualifier
        fields = [
            "code",
            "description",
            "valid_between",
            "update_type",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class MeasurementSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    measurement_unit = MeasurementUnitSerializer(read_only=True)
    measurement_unit_qualifier = MeasurementUnitQualifierSerializer(read_only=True)

    class Meta:
        model = models.Measurement
        fields = [
            "measurement_unit",
            "measurement_unit_qualifier",
            "valid_between",
            "update_type",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class MonetaryUnitSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    code = serializers.CharField(validators=[validators.monetary_unit_code_validator])

    class Meta:
        model = models.MonetaryUnit
        fields = [
            "code",
            "description",
            "valid_between",
            "update_type",
            "start_date",
            "end_date",
        ]
