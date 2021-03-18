"""Business rules for certificates."""
from common.business_rules import BusinessRule
from common.business_rules import DescriptionsRules
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.business_rules import ValidityPeriodContains
from common.models import TrackedModel


class CET1(UniqueIdentifyingFields):
    """The type of the certificate must be unique."""


class CET2(PreventDeleteIfInUse):
    """The certificate type cannot be deleted if it is used in a certificate."""


class CE2(UniqueIdentifyingFields):
    """The combination certificate type and code must be unique."""

    identifying_fields = ("sid", "certificate_type")


class CE4(ValidityPeriodContains):
    """If a certificate is used in a measure condition then the validity periods
    of the certificate must span the validity period of the measure."""

    contained_field_name = "measurecondition__dependent_measure"


class CE5(PreventDeleteIfInUse):
    """The certificate cannot be deleted if it is used in a measure
    condition."""


class CE6(DescriptionsRules):
    """
    At least one description record is mandatory.

    The start date of the first description period must be equal to the start
    date of the certificate. No two associated description periods for the same
    certificate and language may have the same start date. The validity period
    of the certificate must span the validity period of the certificate
    description.
    """

    model_name = "certificate"


class CE7(ValidityPeriodContained):
    """The validity period of the certificate type must span the validity period
    of the certificate."""

    container_field_name = "certificate_type"


class NoOverlappingDescriptions(BusinessRule):
    """Validity periods for descriptions with the same SID cannot overlap."""

    def validate(self, description):
        if (
            type(description)
            .objects.filter(
                described_certificate__sid=description.described_certificate.sid,
                sid=description.sid,
                valid_between__overlap=description.valid_between,
            )
            .approved_up_to_transaction(description.transaction)
            .exclude(id=description.id)
            .exists()
        ):
            raise self.violation(description)


class ContiguousDescriptions(BusinessRule):
    """Certificate description validity period must be adjacent to the previous
    description's validity period."""

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
