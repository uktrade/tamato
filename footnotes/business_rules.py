"""Business rules for Footnotes and Footnote Types."""
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


class FO5(ValidityPeriodContained):
    """When a footnote is used in a measure the validity period of the footnote
    must span the validity period of the measure."""

    contained_field_name = "footnoteassociationmeasure__footnoted_measure"


class FO6(ValidityPeriodContained):
    """When a footnote is used in a goods nomenclature the validity period of
    the footnote must span the validity period of the association with the goods
    nomenclature."""

    contained_field_name = "footnoteassociationgoodsnomenclature"


class FO9(ValidityPeriodContained):
    """When a footnote is used in an additional code the validity period of the
    footnote must span the validity period of the association with the
    additional code."""

    container_field_name = "footnoteassociationadditionalcode"


class FO11(PreventDeleteIfInUse):
    """When a footnote is used in a measure then the footnote may not be
    deleted."""

    via_relation = "footnoteassociationmeasure"


class FO12(PreventDeleteIfInUse):
    """When a footnote is used in a goods nomenclature then the footnote may not
    be deleted."""

    via_relation = "footnoteassociationgoodsnomenclature"


class FO15(PreventDeleteIfInUse):
    """When a footnote is used in an additional code then the footnote may not
    be deleted."""

    via_relation = "footnoteassociationadditionalcode"


class FO17(ValidityPeriodContained):
    """The validity period of the footnote type must span the validity period of
    the footnote."""

    container_field_name = "footnote_type"
