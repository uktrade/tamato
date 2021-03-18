"""Business rules for Additional Codes."""
from django.core.exceptions import ObjectDoesNotExist

from additional_codes.validators import ApplicationCode
from common.business_rules import BusinessRule
from common.business_rules import DescriptionsRules
from common.business_rules import NoOverlapping
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.business_rules import ValidityPeriodContains


class CT1(UniqueIdentifyingFields):
    """The additional code type must be unique."""


class ACN1(UniqueIdentifyingFields):
    """The combination of additional code type + additional code + start date
    must be unique."""

    identifying_fields = ("type", "code", "valid_between__lower")


class ACN2(BusinessRule):
    """The referenced additional code type must exist and have as application
    code "non-Meursing" or "Export Refund for Processed Agricultural Goods."""

    def validate(self, additional_code):
        try:
            if additional_code.type.application_code not in {
                ApplicationCode.ADDITIONAL_CODES,
                ApplicationCode.EXPORT_REFUND_AGRI,
            }:
                raise self.violation(
                    model=additional_code,
                    message=(
                        "The referenced additional code type must have as application "
                        'code "non-Meursing" or "Export Refund for Processed '
                        'Agricultural Goods".'
                    ),
                )

        except ObjectDoesNotExist:
            raise self.violation(
                model=additional_code,
                message="The referenced additional code type must exist.",
            )


class ACN4(NoOverlapping):
    """The validity period of the additional code must not overlap any other
    additional code with the same additional code type + additional code + start
    date."""

    identifying_fields = (
        "type__sid",
        "code",
        "valid_between__lower",
    )


class ACN13(ValidityPeriodContains):
    """When an additional code is used in an additional code nomenclature
    measure then the validity period of the additional code must span the
    validity period of the measure."""

    contained_field_name = "measure"


class ACN17(ValidityPeriodContained):
    """The validity period of the additional code type must span the validity
    period of the additional code."""

    container_field_name = "type"


class ACN5(DescriptionsRules):
    """
    At least one description is mandatory.

    The start date of the first description period must be equal to the start
    date of the additional code. No two associated description periods may have
    the same start date. The start date must be less than or equal to the end
    date of the additional code.
    """

    model_name = "additional code"


class ACN14(PreventDeleteIfInUse):
    """An additional code cannot be deleted if it is used in an additional code
    nomenclature measure."""
