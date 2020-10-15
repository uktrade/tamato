from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db import models
from django.db.models.functions import Lower

from additional_codes import validators
from common.models import NumericSID
from common.models import ShortDescription
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

    def __str__(self):
        return f"AdditionalcodeType {self.sid}: {self.description}"

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_additional_code_types",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        ]


class AdditionalCode(TrackedModel, ValidityMixin):
    """The additional code identifies a piece of text associated with a goods
    nomenclature code within a measure. An additional code can be re-used over time.
    """

    record_code = "245"
    subrecord_code = "00"

    sid = NumericSID()
    type = models.ForeignKey(AdditionalCodeType, on_delete=models.PROTECT)
    code = models.CharField(
        max_length=3, validators=[validators.additional_code_validator]
    )

    def get_description(self):
        return self.descriptions.last()

    def clean(self):
        validators.validate_additional_code_type(self)
        validators.validate_additional_code_type_validity_includes_additional_code_validity(
            self
        )

    def validate_workbasket(self):
        validators.validate_at_least_one_description(self)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_additional_codes",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
            ExclusionConstraint(
                name="exclude_overlapping_additional_codes_ACN1",
                expressions=[
                    (Lower("valid_between"), RangeOperators.EQUAL),
                    ("type", RangeOperators.EQUAL),
                    ("code", RangeOperators.EQUAL),
                ],
            ),
        ]


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
    description_period_sid = NumericSID()

    described_additional_code = models.ForeignKey(
        AdditionalCode, on_delete=models.PROTECT, related_name="descriptions"
    )
    description = models.TextField()

    identifying_fields = ("description_period_sid",)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_additional_code_descriptions",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("described_additional_code", RangeOperators.EQUAL),
                ],
            ),
        ]

    def clean(self):
        validators.validate_description_is_not_null(self)
        validators.validate_first_additional_code_description_has_additional_code_start_date(
            self
        )
        validators.validate_additional_code_description_dont_have_same_start_date(self)
        validators.validate_additional_code_description_start_date_before_additional_code_end_date(
            self
        )

    def __str__(self):
        return (
            f'description - "{self.description}" for {self.described_additional_code}'
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
