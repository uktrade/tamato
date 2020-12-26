"""Business rules for certificates."""
from common.business_rules import BusinessRule
from common.business_rules import find_duplicate_start_dates
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.models import TrackedModel


class CET1(UniqueIdentifyingFields):
    """The type of the certificate must be unique."""


class CET2(PreventDeleteIfInUse):
    """The certificate type cannot be deleted if it is used in a certificate."""


class CE2(UniqueIdentifyingFields):
    """The combination certificate type and code must be unique."""

    identifying_fields = ("sid", "certificate_type")


class CE4(BusinessRule):
    """If a certificate is used in a measure condition then the validity periods of the
    certificate must span the validity period of the measure.
    """

    def validate(self, certificate):
        if (
            certificate.measurecondition_set.model.objects.filter(
                required_certificate__sid=certificate.sid,
            )
            .exclude(
                dependent_measure__valid_between__contained_by=certificate.valid_between,
            )
            .exists()
        ):
            raise self.violation(certificate)


class CE5(PreventDeleteIfInUse):
    """The certificate cannot be deleted if it is used in a measure condition."""


class CE6(BusinessRule):
    """At least one description record is mandatory. The start date of the first
    description period must be equal to the start date of the certificate. No two
    associated description periods for the same certificate and language may have the
    same start date. The validity period of the certificate must span the validity
    period of the certificate description.
    """

    def validate(self, certificate):
        descriptions = certificate.descriptions.order_by("valid_between")

        if descriptions.count() < 1:
            raise self.violation(
                f"Certificate {certificate}: At least one description record is mandatory."
            )

        if descriptions.first().valid_between.lower != certificate.valid_between.lower:
            raise self.violation(
                f"Certificate {certificate}: The first description for the footnote must "
                "have the same start date as the certificate."
            )

        if find_duplicate_start_dates(descriptions).exists():
            raise self.violation(
                f"Certificate {certificate}: No two certficate descriptions may have the "
                "same start date."
            )

        if descriptions.exclude(
            valid_between__contained_by=certificate.valid_between,
        ).exists():
            raise self.violation(
                f"Certificate {certificate}: The validity period of the certificate must "
                "span the validity period of the certificate description."
            )


class CE7(ValidityPeriodContained):
    """The validity period of the certificate type must span the validity period of the
    certificate.
    """

    container_field_name = "certificate_type"


class NoOverlappingDescriptions(BusinessRule):
    """Validity periods for descriptions with the same SID cannot overlap."""

    # XXX implemented to match behaviour of ExclusionConstraint, but I think the
    # original logic is wrong. Won't this prevent updates and deletes?

    def validate(self, description):
        if (
            type(description)
            .objects.filter(
                described_certificate__sid=description.described_certificate.sid,
                sid=description.sid,
                valid_between__overlap=description.valid_between,
            )
            .exclude(id=description.id)
            .exists()
        ):
            raise self.violation(description)


class ContiguousDescriptions(BusinessRule):
    """Certificate description validity period must be adjacent to the previous
    description's validity period.
    """

    def validate(self, description: TrackedModel):
        # XXX Predecessor is previous version of the same description. Shouldn't this
        # check that all current descriptions are adjacent to each other?

        if (
            type(description)
            .objects.filter(
                version_group=description.version_group,
                valid_between__startswith=description.valid_between.lower,
            )
            .exclude(pk=description.pk)
            .exists()
        ):
            raise self.violation(description)
