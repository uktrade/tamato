from django.db import models
from django.db.models import Max

from additional_codes import business_rules
from additional_codes import validators
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.fields import LongDescription
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models.mixins.description import DescribedMixin
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.validity import ValidityMixin
from footnotes import business_rules as footnotes_business_rules
from measures import business_rules as measures_business_rules


class AdditionalCodeType(TrackedModel, ValidityMixin):
    """
    The additional code type allows all additional codes to be classified
    according to type.

    It will be used to check if a given additional code can be associated with
    other data. For example, additional code types for export refund purposes
    are grouped together and can only be used within that area (nomenclature,
    measures).
    """

    record_code = "120"
    subrecord_code = "00"

    description_record_code = "120"
    description_subrecord_code = "05"

    identifying_fields = ("sid",)

    sid = models.CharField(
        max_length=1,
        validators=[validators.additional_code_type_sid_validator],
        db_index=True,
    )
    description = ShortDescription()

    # Code which indicates to which data type the additional code type applies.
    application_code = models.PositiveSmallIntegerField(
        choices=validators.ApplicationCode.choices,
    )

    indirect_business_rules = (
        business_rules.ACN2,
        business_rules.ACN17,
        measures_business_rules.ME12,
    )
    business_rules = (business_rules.CT1, UpdateValidity, UniqueIdentifyingFields)

    def __str__(self):
        return f"AdditionalcodeType {self.sid}: {self.description}"


class AdditionalCode(TrackedModel, ValidityMixin, DescribedMixin):
    """
    The additional code identifies a piece of text associated with a goods
    nomenclature code within a measure.

    An additional code can be re-used over time.
    """

    record_code = "245"
    subrecord_code = "00"

    identifying_fields = ("sid",)

    sid = SignedIntSID(db_index=True)
    type = models.ForeignKey(AdditionalCodeType, on_delete=models.PROTECT)
    code = models.CharField(
        max_length=3,
        validators=[validators.additional_code_validator],
    )

    indirect_business_rules = (
        footnotes_business_rules.FO15,
        footnotes_business_rules.FO9,
        measures_business_rules.ME1,
    )
    business_rules = (
        business_rules.ACN1,
        business_rules.ACN2,
        business_rules.ACN4,
        business_rules.ACN5,
        business_rules.ACN13,
        business_rules.ACN14,
        business_rules.ACN17,
        UpdateValidity,
        UniqueIdentifyingFields,
    )

    def __str__(self):
        return f"{self.type.sid}{self.code}"

    @property
    def autocomplete_label(self):
        return f"{self} - {self.get_description().description}"


class AdditionalCodeDescription(DescriptionMixin, TrackedModel):
    """
    The additional code description contains the description of the additional
    code for a particular period.

    This model combines the additional code description and the additional code
    description period domain objects, because we only care about 1 language.
    """

    record_code = "245"
    subrecord_code = "10"
    period_record_code = "245"
    period_subrecord_code = "05"

    identifying_fields = ("sid",)

    # Store the additional code description period sid so that we can send it in TARIC3
    # updates to systems that expect it.
    sid = SignedIntSID(db_index=True)

    described_additionalcode = models.ForeignKey(
        AdditionalCode,
        on_delete=models.PROTECT,
        related_name="descriptions",
    )
    description = LongDescription()

    indirect_business_rules = (business_rules.ACN5,)

    def save(self, *args, **kwargs):
        if getattr(self, "sid") is None:
            highest_sid = AdditionalCodeDescription.objects.aggregate(Max("sid"))[
                "sid__max"
            ]
            self.sid = highest_sid + 1

        return super().save(*args, **kwargs)

    class Meta:
        ordering = ("validity_start",)


class FootnoteAssociationAdditionalCode(TrackedModel, ValidityMixin):
    """A footnote may be associated with an additional code for part of the
    validity period of the footnote and part of the validity period of the
    additional code."""

    # This is not used and here only for historical data

    record_code = "245"
    subrecord_code = "15"

    identifying_fields = (
        "additional_code__sid",
        "associated_footnote__footnote_id",
        "associated_footnote__footnote_type__footnote_type_id",
    )

    additional_code = models.ForeignKey(AdditionalCode, on_delete=models.PROTECT)
    associated_footnote = models.ForeignKey(
        "footnotes.Footnote",
        on_delete=models.PROTECT,
    )
    business_rules = (UpdateValidity,)
