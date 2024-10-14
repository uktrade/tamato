from django.db import models
from psycopg.types.range import DateRange


class AdditionalCodeTypeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    application_code = models.SmallIntegerField()


class AdditionalCodeTypeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(AdditionalCodeTypeLatest, models.DO_NOTHING)


class AdditionalCodeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    code = models.CharField(max_length=3)
    type = models.ForeignKey(AdditionalCodeTypeLookUp, models.DO_NOTHING)


class AdditionalCodeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(AdditionalCodeLatest, models.DO_NOTHING)


class AdditionalCodeDescriptionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_additionalcode = models.ForeignKey(
        AdditionalCodeLookUp,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class AdditionalCodeDescriptionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        AdditionalCodeDescriptionLatest,
        models.DO_NOTHING,
    )
