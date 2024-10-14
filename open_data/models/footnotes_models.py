from django.db import models
from psycopg.types.range import DateRange


class FootnoteTypeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    footnote_type_id = models.CharField(max_length=3)
    application_code = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class FootnoteTypeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(FootnoteTypeLatest, models.DO_NOTHING)


class FootnoteLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    footnote_id = models.CharField(max_length=5)
    footnote_type = models.ForeignKey("FootnoteTypeLookUp", models.DO_NOTHING)


class FootnoteLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(FootnoteLatest, models.DO_NOTHING)


class FootnoteDescriptionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)
    sid = models.IntegerField()
    described_footnote = models.ForeignKey(FootnoteLookUp, models.DO_NOTHING)
    validity_start = models.DateField()


class FootnoteDescriptionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(FootnoteDescriptionLatest, models.DO_NOTHING)
