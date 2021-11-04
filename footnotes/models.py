from typing import Type

from django.db import models
from django.db.models import Max

from common.business_rules import UpdateValidity
from common.fields import LongDescription
from common.fields import ShortDescription
from common.fields import SignedIntSID
from common.models import TrackedModel
from common.models.mixins.description import DescribedMixin
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.validity import ValidityMixin
from footnotes import business_rules
from footnotes import validators
from measures import business_rules as measures_business_rules


class FootnoteType(TrackedModel, ValidityMixin):
    """
    The footnote type record allows all footnotes to be classified according to
    type.

    It will be used to check if a given footnote can be associated with a
    specific entity. For example, footnote type "CN" will be used to group all
    CN-related footnotes.
    """

    record_code = "100"
    subrecord_code = "00"

    description_record_code = "100"
    description_subrecord_code = "05"

    identifying_fields = ("footnote_type_id",)

    footnote_type_id = models.CharField(
        max_length=3,
        validators=[validators.footnote_type_id_validator],
        db_index=True,
    )
    application_code = models.PositiveIntegerField(
        choices=validators.ApplicationCode.choices,
    )
    description = ShortDescription()

    indirect_business_rules = (business_rules.FO17,)
    business_rules = (
        business_rules.FOT1,
        business_rules.FOT2,
        UpdateValidity,
    )

    def __str__(self):
        return self.footnote_type_id

    def in_use(self):
        return (
            Footnote.objects.filter(
                footnote_type__footnote_type_id=self.footnote_type_id,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )


class Footnote(TrackedModel, ValidityMixin, DescribedMixin):
    """A footnote relates to a piece of text, and either clarifies it (in the
    case of nomenclature) or limits its application (as in the case of
    measures)."""

    record_code = "200"
    subrecord_code = "00"

    footnote_id = models.CharField(
        max_length=5,
        validators=[validators.footnote_id_validator],
        db_index=True,
    )
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)

    identifying_fields = ("footnote_id", "footnote_type__footnote_type_id")

    indirect_business_rules = (
        measures_business_rules.ME71,
        measures_business_rules.ME73,
    )
    business_rules = (
        business_rules.FO2,
        business_rules.FO4,
        business_rules.FO5,
        business_rules.FO6,
        business_rules.FO9,
        business_rules.FO11,
        business_rules.FO12,
        business_rules.FO15,
        business_rules.FO17,
        UpdateValidity,
    )

    def __str__(self):
        return f"{self.footnote_type.footnote_type_id}{self.footnote_id}"

    @property
    def autocomplete_label(self):
        return f"{self} - {self.get_description().description}"

    def _used_in(self, dependent_type: Type[TrackedModel]):
        return (
            dependent_type.objects.filter(
                associated_footnote__footnote_id=self.footnote_id,
                associated_footnote__footnote_type__footnote_type_id=self.footnote_type.footnote_type_id,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )

    def used_in_additional_code(self):
        return self._used_in(self.footnoteassociationadditionalcode_set.model)

    def used_in_goods_nomenclature(self):
        return self._used_in(self.footnoteassociationgoodsnomenclature_set.model)

    def used_in_measure(self):
        return self._used_in(self.footnoteassociationmeasure_set.model)

    def in_use(self):
        return (
            self.used_in_additional_code()
            or self.used_in_goods_nomenclature()
            or self.used_in_measure()
        )

    class Meta:
        ordering = ["footnote_type__footnote_type_id", "footnote_id"]


class FootnoteDescription(DescriptionMixin, TrackedModel):
    """
    The footnote description contains the text associated with a footnote, for a
    given language and for a particular period.

    Description period(s) associated with footnote text. The description of a
    footnote may change independently of the footnote id. The footnote
    description period contains the validity start date of the footnote
    description.
    """

    record_code = "200"
    subrecord_code = "10"

    period_record_code = "200"
    period_subrecord_code = "05"

    described_footnote = models.ForeignKey(
        Footnote,
        on_delete=models.CASCADE,
        related_name="descriptions",
    )
    description = LongDescription()
    sid = SignedIntSID(db_index=True)

    indirect_business_rules = (business_rules.FO4,)

    def save(self, *args, **kwargs):
        if getattr(self, "sid") is None:
            highest_sid = FootnoteDescription.objects.aggregate(Max("sid"))["sid__max"]
            self.sid = highest_sid + 1

        return super().save(*args, **kwargs)

    class Meta:
        ordering = ("validity_start",)
