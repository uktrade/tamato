"""Business rules for Additional Codes."""
from django.core.exceptions import ObjectDoesNotExist

from additional_codes.validators import ApplicationCode
from common.business_rules import BusinessRule
from common.business_rules import DescriptionsRules
from common.business_rules import find_duplicate_start_dates
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained


class CT1(UniqueIdentifyingFields):
    """The additional code type must be unique."""


class ACN1(UniqueIdentifyingFields):
    """The combination of additional code type + additional code + start date must be
    unique.
    """

    identifying_fields = ("type", "code", "valid_between__lower")


class ACN2(BusinessRule):
    """The referenced additional code type must exist and have as application code
    "non-Meursing" or "Export Refund for Processed Agricultural Goods.
    """

    def validate(self, additional_code):
        try:
            if additional_code.type.application_code not in {
                ApplicationCode.ADDITIONAL_CODES,
                ApplicationCode.EXPORT_REFUND_AGRI,
            }:
                raise self.violation(
                    f"AdditionalCode {additional_code}: The referenced additional code "
                    'type must have as application code "non-Meursing" or "Export Refund '
                    'for Processed Agricultural Goods".'
                )

        except ObjectDoesNotExist:
            raise self.violation(
                f"AdditionalCode {additional_code}: The referenced additional code type "
                "must exist."
            )


class ACN4(BusinessRule):
    """The validity period of the additional code must not overlap any other additional
    code with the same additional code type + additional code + start date.
    """

    def validate(self, additional_code):
        if (
            type(additional_code)
            .objects.filter(
                type__sid=additional_code.type.sid,
                code=additional_code.code,
                valid_between__startswith=additional_code.valid_between.lower,
                valid_between__overlap=additional_code.valid_between,
            )
            .current()
            .exists()
        ):
            raise self.violation(additional_code)


class ACN13(BusinessRule):
    """When an additional code is used in an additional code nomenclature measure then
    the validity period of the additional code must span the validity period of the
    measure.
    """

    def validate(self, additional_code):
        Measure = additional_code.measure_set.model
        if (
            Measure.objects.filter(
                additional_code__sid=additional_code.sid,
            )
            .with_effective_valid_between()
            .current()
            .exclude(
                db_effective_valid_between__contained_by=additional_code.valid_between,
            )
            .exists()
        ):
            raise self.violation(additional_code)


class ACN17(ValidityPeriodContained):
    """The validity period of the additional code type must span the validity period of
    the additional code.
    """

    container_field_name = "type"


class ACN5(DescriptionsRules):
    """At least one description is mandatory. The start date of the first description
    period must be equal to the start date of the additional code. No two associated
    description periods may have the same start date. The start date must be less than
    or equal to the end date of the additional code.
    """

    model_name = "additional code"


class ACN14(PreventDeleteIfInUse):
    """An additional code cannot be deleted if it is used in an additional code
    nomenclature measure.
    """
