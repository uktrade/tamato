from django.db import models

from certificates import validators
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models import ValidityMixin


class CertificateType(TrackedModel, ValidityMixin):
    record_code = "110"
    subrecord_code = "00"

    description_record_code = "110"
    description_subrecord_code = "05"

    sid = models.CharField(
        max_length=1, validators=[validators.certificate_type_sid_validator]
    )
    description = ShortDescription()

    def in_use(self):
        # TODO handle deletes
        return Certificate.objects.filter(certificate_type__sid=self.sid).exists()

    def __str__(self):
        return self.sid


class Certificate(TrackedModel, ValidityMixin):
    record_code = "205"
    subrecord_code = "00"
    sid = models.CharField(
        max_length=3, validators=[validators.certificate_sid_validator]
    )

    certificate_type = models.ForeignKey(
        CertificateType, related_name="certificates", on_delete=models.PROTECT
    )

    @property
    def code(self):
        return self.certificate_type.sid + self.sid

    def __str__(self):
        return self.code

    def in_use(self):
        # TODO handle deletes
        return self.measurecondition_set.model.objects.filter(
            required_certificate__sid=self.sid,
        ).exists()


class CertificateDescription(TrackedModel, ValidityMixin):
    record_code = "205"
    subrecord_code = "10"

    period_record_code = "205"
    period_subrecord_code = "05"

    sid = SignedIntSID()

    description = ShortDescription()
    described_certificate = models.ForeignKey(
        Certificate, related_name="descriptions", on_delete=models.PROTECT
    )

    def __str__(self):
        return self.identifying_fields_to_string(
            identifying_fields=("described_certificate", "valid_between")
        )
