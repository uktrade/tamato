from django.db import models

from common.models import ValidityMixin


class NationalMixin(models.Model):
    national = models.BooleanField(default=False)

    class Meta:
        abstract = True


class FootnoteType(ValidityMixin, NationalMixin):
    id = models.CharField(primary_key=True, max_length=2, null=False, blank=True)
    application_code = models.IntegerField()
    description = models.TextField()


class Footnote(ValidityMixin, NationalMixin):
    id = models.CharField(primary_key=True, max_length=5, null=False, blank=True)
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)


class FootnoteDescription(NationalMixin):
    footnote = models.ForeignKey(Footnote, on_delete=models.PROTECT)
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)
    description = models.TextField()


class FootnoteDescriptionPeriod(ValidityMixin, NationalMixin):
    footnote = models.ForeignKey(Footnote, on_delete=models.PROTECT)
    footnote_type = models.ForeignKey(FootnoteType, on_delete=models.PROTECT)
    footnote_description = models.ForeignKey(
        FootnoteDescription, on_delete=models.PROTECT
    )
