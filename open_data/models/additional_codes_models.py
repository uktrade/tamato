from django.db import models
from psycopg.types.range import DateRange


class ReportAdditionalCodeType(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    application_code = models.SmallIntegerField()


class ReportAdditionalCode(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    code = models.CharField(max_length=3)
    type = models.ForeignKey(ReportAdditionalCodeType, models.DO_NOTHING)


class ReportAdditionalCodeDescription(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_additionalcode = models.ForeignKey(
        ReportAdditionalCode,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()
