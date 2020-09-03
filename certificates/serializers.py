from rest_framework import serializers

from certificates import models
from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.validators import NumericSIDValidator


@TrackedModelSerializer.register_polymorphic_model
class CertificateTypeSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    class Meta:
        model = models.CertificateType
        fields = [
            "sid",
            "description",
            "update_type",
            "record_code",
            "subrecord_code",
            "description_record_code",
            "description_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class CertificateSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    certificate_type = CertificateTypeSerializer(read_only=True)

    class Meta:
        model = models.Certificate
        fields = [
            "sid",
            "certificate_type",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class CertificateDescriptionSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    described_certificate = CertificateSerializer(read_only=True)
    sid = serializers.IntegerField(validators=[NumericSIDValidator()])

    class Meta:
        model = models.CertificateDescription
        fields = [
            "sid",
            "described_certificate",
            "description",
            "update_type",
            "record_code",
            "subrecord_code",
            "period_record_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]
