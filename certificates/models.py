from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.core.validators import MaxValueValidator
from django.db import models

from certificates import validators
from common.models import TrackedModel
from common.models import ValidityMixin


class CertificateType(TrackedModel, ValidityMixin):
    sid = models.CharField(
        max_length=1, validators=[validators.certificate_type_sid_validator]
    )
    description = models.CharField(max_length=500, null=False, blank=False)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        validators.validate_description_is_not_null(self)

    def __str__(self):
        return f"Certificate Type: {self.sid} - {self.description}"

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_certificate_types",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        )


class Certificate(TrackedModel, ValidityMixin):
    sid = models.CharField(
        max_length=3, validators=[validators.certificate_sid_validator]
    )

    certificate_type = models.ForeignKey(
        CertificateType, related_name="certificates", on_delete=models.PROTECT
    )

    @property
    def code(self):
        return self.certificate_type.sid + self.sid

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        validators.validate_certificate_type_validity_includes_certificate_validity(
            self
        )

    def validate_workbasket(self):
        validators.validate_at_least_one_description(self)

    def __str__(self):
        return f"Certificate {self.code}"

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_certificates",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        )


class CertificateDescription(TrackedModel, ValidityMixin):
    sid = models.PositiveIntegerField(validators=[MaxValueValidator(99999999)])

    description = models.CharField(max_length=500, null=False, blank=False)
    described_certificate = models.ForeignKey(
        Certificate, related_name="descriptions", on_delete=models.PROTECT
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        validators.validate_description_is_not_null(self)
        validators.validate_first_certificate_description_has_certificate_start_date(
            self
        )
        validators.validate_certificate_description_dont_have_same_start_date(self)
        validators.validate_previous_certificate_description_is_adjacent(self)

    def __str__(self):
        return f"Certificate Description for {self.certificate}: {self.description}"

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_certificate_descriptions",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        )
