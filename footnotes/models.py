from django.db import models

from common.models import ValidityMixin


class FootnoteType(ValidityMixin):
    footnote_type_id = models.CharField(unique=True, max_length=2)
    description = models.CharField(max_length=500)


class Footnote(ValidityMixin):
    footnote_id = models.CharField(unique=True, max_length=5)
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)
    description = models.CharField(max_length=500)

    class Meta:
        ordering = ["footnote_type__footnote_type_id", "footnote_id"]
