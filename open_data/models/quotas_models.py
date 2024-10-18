from django.db import models
from psycopg.types.range import DateRange


class QuotaAssociationLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sub_quota_relation_type = models.CharField(max_length=2)
    coefficient = models.DecimalField(max_digits=16, decimal_places=5)
    main_quota = models.ForeignKey("QuotaDefinitionLookUp", models.DO_NOTHING)
    sub_quota = models.ForeignKey(
        "QuotaDefinitionLookUp",
        models.DO_NOTHING,
        related_name="quotasquotaassociation_sub_quota_set",
    )


class QuotaAssociationLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaAssociationLatest, models.DO_NOTHING)


class QuotaDefinitionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    volume = models.DecimalField(max_digits=14, decimal_places=3)
    initial_volume = models.DecimalField(max_digits=14, decimal_places=3)
    maximum_precision = models.SmallIntegerField()
    quota_critical = models.BooleanField()
    quota_critical_threshold = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    measurement_unit = models.ForeignKey(
        "MeasurementUnitLookup",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    measurement_unit_qualifier = models.ForeignKey(
        "MeasurementUnitQualifierLookUp",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    monetary_unit = models.ForeignKey(
        "MonetaryunitLookUp",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    order_number = models.ForeignKey("QuotaOrderNumberLookUp", models.DO_NOTHING)


class QuotaDefinitionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaDefinitionLatest, models.DO_NOTHING)


class QuotaOrderNumberLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    order_number = models.CharField(max_length=6)
    mechanism = models.SmallIntegerField()
    category = models.SmallIntegerField()


class QuotaOrderNumberLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaOrderNumberLatest, models.DO_NOTHING)


class QuotaOrderNumberOriginLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    geographical_area = models.ForeignKey("GeographicalAreaLookUp", models.DO_NOTHING)
    order_number = models.ForeignKey(QuotaOrderNumberLookUp, models.DO_NOTHING)


class QuotaOrderNumberOriginLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaOrderNumberOriginLatest, models.DO_NOTHING)


class QuotaSuspensionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(QuotaDefinitionLookUp, models.DO_NOTHING)


class QuotaSuspensionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaSuspensionLatest, models.DO_NOTHING)


class QuotaOrderNumberOriginExclusionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    excluded_geographical_area = models.ForeignKey(
        "GeographicalAreaLookUp",
        models.DO_NOTHING,
    )
    origin = models.ForeignKey(QuotaOrderNumberOriginLookUp, models.DO_NOTHING)


class QuotaOrderNumberOriginExclusionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        QuotaOrderNumberOriginExclusionLatest,
        models.DO_NOTHING,
    )


class QuotaEventLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    subrecord_code = models.CharField(max_length=2)
    occurrence_timestamp = models.DateTimeField()
    data = models.JSONField()
    quota_definition = models.ForeignKey(QuotaDefinitionLookUp, models.DO_NOTHING)


class QuotaEventLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaEventLatest, models.DO_NOTHING)


class QuotaBlockingLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    blocking_period_type = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(QuotaDefinitionLookUp, models.DO_NOTHING)


class QuotaBlockingLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(QuotaBlockingLatest, models.DO_NOTHING)
