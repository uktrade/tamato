from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db import models
from django.db.models import Q
from django.urls import reverse

from common.models import NumericSID
from common.models import ShortDescription
from common.models import TimestampedMixin
from common.models import TrackedModel
from common.models import ValidityMixin
from footnotes import validators
from workbaskets.validators import WorkflowStatus


class FootnoteType(TrackedModel, ValidityMixin):
    """The footnote type record allows all footnotes to be classified according to type.
    It will be used to check if a given footnote can be associated with a specific
    entity. For example, footnote type "CN" will be used to group all CN-related
    footnotes.
    """

    record_code = "100"
    subrecord_code = "00"

    description_record_code = "100"
    description_subrecord_code = "05"

    identifying_fields = ("footnote_type_id",)

    footnote_type_id = models.CharField(
        max_length=3, validators=[validators.footnote_type_id_validator]
    )
    application_code = models.PositiveIntegerField(
        choices=validators.ApplicationCode.choices
    )
    description = ShortDescription()

    def __str__(self):
        return f"{self.footnote_type_id} - {self.description}"

    def clean(self):
        validators.validate_description_is_not_null(self)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_footnote_types",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("footnote_type_id", RangeOperators.EQUAL),
                ],
            ),
        ]


class Footnote(TrackedModel, TimestampedMixin, ValidityMixin):
    """A footnote relates to a piece of text, and either clarifies it (in the case of
    nomenclature) or limits its application (as in the case of measures).
    """

    record_code = "200"
    subrecord_code = "00"

    footnote_id = models.CharField(
        max_length=5, validators=[validators.footnote_id_validator]
    )
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)

    identifying_fields = ("footnote_id", "footnote_type")

    def __str__(self):
        return f"{self.footnote_type.footnote_type_id}{self.footnote_id}"

    def get_url(self, action="detail"):
        return reverse(
            f"footnote-ui-{action}",
            kwargs={
                "footnote_type__footnote_type_id": self.footnote_type.footnote_type_id,
                "footnote_id": self.footnote_id,
            },
        )

    def get_descriptions(self, workbasket=None):
        return (
            FootnoteDescription.objects.current()
            .filter(
                described_footnote__footnote_id=self.footnote_id,
                described_footnote__footnote_type=self.footnote_type,
            )
            .with_workbasket(workbasket)
        )

    def get_description(self):
        return self.get_descriptions().last()

    def clean(self):
        validators.validate_footnote_type_validity_includes_footnote_validity(self)

    def validate_workbasket(self):
        validators.validate_unique_type_and_id(self)
        validators.validate_at_least_one_description(self)

    class Meta:
        ordering = ["footnote_type__footnote_type_id", "footnote_id"]


class FootnoteDescription(TrackedModel, ValidityMixin):
    """
    The footnote description contains the text associated with a footnote, for a given
    language and for a particular period.

    Description period(s) associated with footnote text. The description of a footnote
    may change independently of the footnote id. The footnote description period
    contains the validity start date of the footnote description.
    """

    record_code = "200"
    subrecord_code = "10"

    period_record_code = "200"
    period_subrecord_code = "05"

    described_footnote = models.ForeignKey(
        Footnote, on_delete=models.CASCADE, related_name="descriptions"
    )
    description = models.TextField()
    description_period_sid = NumericSID()

    identifying_fields = ("description_period_sid",)

    def __str__(self):
        return self.description

    def clean(self):
        validators.validate_first_footnote_description_has_footnote_start_date(self)
        validators.validate_footnote_description_start_date_before_footnote_end_date(
            self
        )

    def validate_workbasket(self):
        validators.validate_footnote_description_dont_have_same_start_date(self)

    def get_url(self, action="detail"):
        return reverse(
            f"footnote-ui-description-{action}",
            kwargs={
                "described_footnote__footnote_type__footnote_type_id": self.described_footnote.footnote_type.footnote_type_id,
                "described_footnote__footnote_id": self.described_footnote.footnote_id,
                "description_period_sid": self.description_period_sid,
            },
        )
