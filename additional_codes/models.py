from django.db import models

from additional_codes import validators
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models import ValidityMixin


class AdditionalCodeType(TrackedModel, ValidityMixin):
    """The additional code type allows all additional codes to be classified according
    to type. It will be used to check if a given additional code can be associated with
    other data. For example, additional code types for export refund purposes are
    grouped together and can only be used within that area (nomenclature, measures).
    """

    record_code = "120"
    subrecord_code = "00"

    description_record_code = "120"
    description_subrecord_code = "05"

    sid = models.CharField(
        max_length=1,
        validators=[validators.additional_code_type_sid_validator],
    )
    description = ShortDescription()

    # Code which indicates to which data type the additional code type applies.
    application_code = models.PositiveSmallIntegerField(
        choices=validators.ApplicationCode.choices,
    )


class AdditionalCode(TrackedModel, ValidityMixin):
    """The additional code identifies a piece of text associated with a goods
    nomenclature code within a measure. An additional code can be re-used over time.
    """

    record_code = "245"
    subrecord_code = "00"

    sid = SignedIntSID()
    type = models.ForeignKey(AdditionalCodeType, on_delete=models.PROTECT)
    code = models.CharField(
        max_length=3, validators=[validators.additional_code_validator]
    )

    def get_description(self):
        return self.descriptions.last()

    def in_use(self):
        # TODO handle deletes
        return self.measure_set.model.objects.filter(
            additional_code__sid=self.sid,
        ).exists()


class AdditionalCodeDescription(TrackedModel, ValidityMixin):
    """The additional code description contains the description of the additional code
    for a particular period.

    This model combines the additional code description and the additional code
    description period domain objects, because we only care about 1 language.
    """

    record_code = "245"
    subrecord_code = "10"
    period_record_code = "245"
    period_subrecord_code = "05"

    # Store the additional code description period sid so that we can send it in TARIC3
    # updates to systems that expect it.
    description_period_sid = SignedIntSID()

    described_additional_code = models.ForeignKey(
        AdditionalCode, on_delete=models.PROTECT, related_name="descriptions"
    )
    description = models.TextField()

    identifying_fields = ("description_period_sid",)

    def __str__(self):
        return self.identifying_fields_to_string(
            identifying_fields=("described_additional_code", "valid_between"),
        )


class FootnoteAssociationAdditionalCode(TrackedModel, ValidityMixin):
    """A footnote may be associated with an additional code for part of the validity
    period of the footnote and part of the validity period of the additional code.
    """

    # This is not used and here only for historical data

    record_code = "245"
    subrecord_code = "15"

    additional_code = models.ForeignKey(AdditionalCode, on_delete=models.PROTECT)
    associated_footnote = models.ForeignKey(
        "footnotes.Footnote", on_delete=models.PROTECT
    )
