from django.db import models

from certificates import business_rules
from certificates import validators
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import DescriptionMixin
from common.models import TrackedModel
from common.models import ValidityMixin
from measures import business_rules as measures_business_rules


class CertificateType(TrackedModel, ValidityMixin):
    record_code = "110"
    subrecord_code = "00"

    description_record_code = "110"
    description_subrecord_code = "05"

    sid = models.CharField(
        max_length=1,
        validators=[validators.certificate_type_sid_validator],
        db_index=True,
    )
    description = ShortDescription()

    indirect_business_rules = (business_rules.CE7,)
    business_rules = (
        business_rules.CET1,
        business_rules.CET2,
    )

    def in_use(self):
        return (
            Certificate.objects.filter(certificate_type__sid=self.sid)
            .approved_up_to_transaction(self.transaction)
            .exists()
        )

    def __str__(self):
        return self.sid


class Certificate(TrackedModel, ValidityMixin):
    record_code = "205"
    subrecord_code = "00"
    sid = models.CharField(
        max_length=3,
        validators=[validators.certificate_sid_validator],
        db_index=True,
    )

    certificate_type = models.ForeignKey(
        CertificateType,
        related_name="certificates",
        on_delete=models.PROTECT,
    )

    identifying_fields = (
        "certificate_type__sid",
        "sid",
    )

    indirect_business_rules = (
        measures_business_rules.ME56,
        measures_business_rules.ME57,
    )
    business_rules = (
        business_rules.CE2,
        business_rules.CE4,
        business_rules.CE5,
        business_rules.CE6,
        business_rules.CE7,
    )

    @property
    def code(self):
        return self.certificate_type.sid + self.sid

    def __str__(self):
        return self.code

    def in_use(self):
        return (
            self.measurecondition_set.model.objects.filter(
                required_certificate__sid=self.sid,
                required_certificate__certificate_type=self.certificate_type,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )


class CertificateDescription(DescriptionMixin, ValidityMixin, TrackedModel):
    record_code = "205"
    subrecord_code = "10"

    period_record_code = "205"
    period_subrecord_code = "05"

    sid = SignedIntSID(db_index=True)

    description = ShortDescription()
    described_certificate = models.ForeignKey(
        Certificate,
        related_name="descriptions",
        on_delete=models.PROTECT,
    )

    indirect_business_rules = (business_rules.CE6,)
    business_rules = (
        business_rules.NoOverlappingDescriptions,
        business_rules.ContiguousDescriptions,
    )

    def __str__(self):
        return self.identifying_fields_to_string(
            identifying_fields=("described_certificate", "valid_between"),
        )

    class Meta:
        ordering = ("valid_between",)
