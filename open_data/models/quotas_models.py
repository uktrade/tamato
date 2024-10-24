from django.db import models
from psycopg.types.range import DateRange


class ReportQuotaAssociation(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sub_quota_relation_type = models.CharField(max_length=2)
    coefficient = models.DecimalField(max_digits=16, decimal_places=5)
    main_quota = models.ForeignKey("ReportQuotaDefinition", models.DO_NOTHING)
    sub_quota = models.ForeignKey(
        "QuotaDefinition",
        models.DO_NOTHING,
        related_name="quotasquotaassociation_sub_quota_set",
    )


class ReportQuotaDefinition(models.Model):
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
        "ReportMeasurementUnitLookup",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    measurement_unit_qualifier = models.ForeignKey(
        "ReportMeasurementUnitQualifier",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    monetary_unit = models.ForeignKey(
        "ReportMonetaryunit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    order_number = models.ForeignKey("ReportQuotaOrderNumber", models.DO_NOTHING)


class ReportQuotaOrderNumber(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    order_number = models.CharField(max_length=6)
    mechanism = models.SmallIntegerField()
    category = models.SmallIntegerField()


class ReportQuotaOrderNumberOrigin(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    geographical_area = models.ForeignKey("ReportGeographicalArea", models.DO_NOTHING)
    order_number = models.ForeignKey(ReportQuotaOrderNumber, models.DO_NOTHING)


class ReportQuotaSuspension(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(ReportQuotaDefinition, models.DO_NOTHING)


class ReportQuotaOrderNumberOriginExclusion(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    excluded_geographical_area = models.ForeignKey(
        "GeographicalArea",
        models.DO_NOTHING,
    )
    origin = models.ForeignKey(ReportQuotaOrderNumberOrigin, models.DO_NOTHING)


class ReportQuotaEvent(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    subrecord_code = models.CharField(max_length=2)
    occurrence_timestamp = models.DateTimeField()
    data = models.JSONField()
    quota_definition = models.ForeignKey(ReportQuotaDefinition, models.DO_NOTHING)


class ReportQuotaBlocking(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    blocking_period_type = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(ReportQuotaDefinition, models.DO_NOTHING)
