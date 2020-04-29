from django.db import models

from common.models import ValidityMixin
from footnotes import validators


class FootnoteType(ValidityMixin):
    footnote_type_id = models.CharField(
        unique=True, max_length=3, validators=[validators.valid_footnote_type_id]
    )
    description = models.CharField(max_length=500)


class Footnote(ValidityMixin):
    footnote_id = models.CharField(
        unique=True, max_length=5, validators=[validators.valid_footnote_id]
    )
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)
    description = models.CharField(max_length=500)

    class Meta:
        ordering = ["footnote_type__footnote_type_id", "footnote_id"]
