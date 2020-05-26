from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from common.models import ValidityMixin
from footnotes import validators


"""
Footnote type application codes
"""
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


class FootnoteType(ValidityMixin):
    footnote_type_id = models.CharField(
        unique=True, max_length=3, validators=[validators.FootnoteTypeIDValidator]
    )
    application_code = models.PositiveIntegerField(choices=ApplicationCode.choices)


class FootnoteTypeDescription(models.Model):
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.CASCADE)
    description = models.CharField(max_length=500)


class Footnote(ValidityMixin):
    footnote_id = models.CharField(
        max_length=5, validators=[validators.FootnoteIDValidator]
    )
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["footnote_id", "footnote_type"], name="FO2",
            ),
        ]
        ordering = ["footnote_type__footnote_type_id", "footnote_id"]

    def clean(self):
        validators.valid_footnote_description(self)
        validators.valid_footnote_period(self)


class FootnoteDescription(ValidityMixin):
    footnote = models.ForeignKey(Footnote, on_delete=models.CASCADE)
    description = models.TextField()

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="FO4",
                expressions=[
                    (Lower("valid_between"), RangeOperators.EQUAL),
                    ("footnote", RangeOperators.EQUAL),
                ],
            ),
        ]

    def clean(self):
        validators.valid_footnote_description_period(self)
