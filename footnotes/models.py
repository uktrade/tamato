from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db import models

from common.models import TrackedModel
from common.models import ValidityMixin
from common.validators import NumericSIDValidator
from footnotes import validators


# Footnote type application codes
ApplicationCode = models.IntegerChoices(
    "ApplicationCode",
    [
        "CN nomenclature",
        "TARIC nomenclature",
        "Export refund nomenclature",
        "Wine reference nomenclature",
        "Additional codes",
        "CN measures",
        "Other measures",
        "Meursing Heading",
        "Dynamic footnote",
    ],
)


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

    footnote_type_id = models.CharField(
        max_length=3, validators=[validators.footnote_type_id_validator]
    )
    application_code = models.PositiveIntegerField(choices=ApplicationCode.choices)
    description = models.CharField(max_length=500)

    def __str__(self):
        return f"{self.footnote_type_id} - {self.description}"

    def clean(self):
        validators.validate_description_is_not_null(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

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


class Footnote(TrackedModel, ValidityMixin):
    """A footnote relates to a piece of text, and either clarifies it (in the case of
    nomenclature) or limits its application (as in the case of measures).
    """

    record_code = "200"
    subrecord_code = "00"

    footnote_id = models.CharField(
        max_length=5, validators=[validators.footnote_id_validator]
    )
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.footnote_type.footnote_type_id}{self.footnote_id}"

    def get_description(self):
        return self.descriptions.last()

    def clean(self):
        validators.validate_footnote_type_validity_includes_footnote_validity(self)

    def validate_workbasket(self):
        validators.validate_at_least_one_description(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_footnotes_FO2",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("footnote_id", RangeOperators.EQUAL),
                    ("footnote_type", RangeOperators.EQUAL),
                ],
            ),
        ]
        ordering = ["footnote_type__footnote_type_id", "footnote_id"]


class FootnoteDescription(TrackedModel, ValidityMixin):
    """The footnote type description contains the text associated with a footnote type,
    for a given language and for a particular period. There can only be one description
    of each footnote type. The same description may appear for several footnote types,
    for example "footnotes for measures".
    """

    record_code = "200"
    subrecord_code = "10"

    period_record_code = "200"
    period_subrecord_code = "05"

    described_footnote = models.ForeignKey(
        Footnote, on_delete=models.CASCADE, related_name="descriptions"
    )
    description = models.TextField()
    description_period_sid = models.PositiveIntegerField(
        validators=[NumericSIDValidator()]
    )

    def __str__(self):
        return f'description - "{self.description}" for {self.described_footnote}'

    def clean(self):
        validators.validate_first_footnote_description_has_footnote_start_date(self)
        validators.validate_footnote_description_dont_have_same_start_date(self)
        validators.validate_footnote_description_start_date_before_footnote_end_date(
            self
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="exclude_overlapping_footnote_descriptions",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("described_footnote", RangeOperators.EQUAL),
                ],
            ),
        ]
