"""Business rules for Footnotes and Footnote Types."""
from common.business_rules import BusinessRule
from common.business_rules import DescriptionsRules
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained


class FOT1(UniqueIdentifyingFields):
    """The type of the footnote must be unique."""


class FOT2(PreventDeleteIfInUse):
    """The footnote type cannot be deleted if it is used in a footnote."""


class FO2(UniqueIdentifyingFields):
    """The combination footnote type and code must be unique."""


class FO4(DescriptionsRules):
    model_name = "footnote"


class ValidityPeriodContainsIfInUse(BusinessRule):
    """Rule enforcing footnote validity period spans a dependent's validity
    period."""

    dependent_name: str
    footnoted_model_field_name: str

    def validate(self, footnote):
        assoc = getattr(footnote, f"footnoteassociation{self.dependent_name}_set")
        if (
            assoc.model.objects.filter(
                associated_footnote__footnote_id=footnote.footnote_id,
                associated_footnote__footnote_type__footnote_type_id=footnote.footnote_type.footnote_type_id,
            )
            .current_as_of(footnote.transaction)
            .exclude(
                **{
                    f"{self.footnoted_model_field_name}__valid_between__contained_by": footnote.valid_between,
                }
            )
            .exists()
        ):
            raise self.violation(footnote)


class FO5(ValidityPeriodContainsIfInUse):
    """When a footnote is used in a measure the validity period of the footnote
    must span the validity period of the measure."""

    dependent_name = "measure"
    footnoted_model_field_name = "footnoted_measure"


class FO6(ValidityPeriodContainsIfInUse):
    """When a footnote is used in a goods nomenclature the validity period of
    the footnote must span the validity period of the association with the goods
    nomenclature."""

    dependent_name = "goodsnomenclature"
    footnoted_model_field_name = "goods_nomenclature"


class FO9(ValidityPeriodContainsIfInUse):
    """When a footnote is used in an additional code the validity period of the
    footnote must span the validity period of the association with the
    additional code."""

    dependent_name = "additionalcode"
    footnoted_model_field_name = "additional_code"


class FO11(PreventDeleteIfInUse):
    """When a footnote is used in a measure then the footnote may not be
    deleted."""

    in_use_check = "used_in_measure"


class FO12(PreventDeleteIfInUse):
    """When a footnote is used in a goods nomenclature then the footnote may not
    be deleted."""

    in_use_check = "used_in_goods_nomenclature"


class FO15(PreventDeleteIfInUse):
    """When a footnote is used in an additional code then the footnote may not
    be deleted."""

    in_use_check = "used_in_additional_code"


class FO17(ValidityPeriodContained):
    """The validity period of the footnote type must span the validity period of
    the footnote."""

    container_field_name = "footnote_type"
