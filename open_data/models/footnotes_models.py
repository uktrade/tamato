from django.db import models
from psycopg.types.range import DateRange


class FootnotesFootnote(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    footnote_id = models.CharField(max_length=5)
    footnote_type = models.ForeignKey("FootnotesFootnotetype", models.DO_NOTHING)


class FootnotesFootnotetype(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    footnote_type_id = models.CharField(max_length=3)
    application_code = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class FootnotesFootnotedescription(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)
    sid = models.IntegerField()
    described_footnote = models.ForeignKey(FootnotesFootnote, models.DO_NOTHING)
    validity_start = models.DateField()
