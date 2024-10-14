from django.db import models
from psycopg.types.range import DateRange


class QuotasQuotaassociation(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sub_quota_relation_type = models.CharField(max_length=2)
    coefficient = models.DecimalField(max_digits=16, decimal_places=5)
    main_quota = models.ForeignKey("QuotasQuotadefinition", models.DO_NOTHING)
    sub_quota = models.ForeignKey(
        "QuotasQuotadefinition",
        models.DO_NOTHING,
        related_name="quotasquotaassociation_sub_quota_set",
    )


class QuotasQuotadefinition(models.Model):
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
        "MeasuresMeasurementunit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    measurement_unit_qualifier = models.ForeignKey(
        "MeasuresMeasurementunitqualifier",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    monetary_unit = models.ForeignKey(
        "MeasuresMonetaryunit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    order_number = models.ForeignKey("QuotasQuotaordernumber", models.DO_NOTHING)


class QuotasQuotaordernumber(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    order_number = models.CharField(max_length=6)
    mechanism = models.SmallIntegerField()
    category = models.SmallIntegerField()


class QuotasQuotaordernumberorigin(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    geographical_area = models.ForeignKey("GeoAreasGeographicalarea", models.DO_NOTHING)
    order_number = models.ForeignKey(QuotasQuotaordernumber, models.DO_NOTHING)


class QuotasQuotasuspension(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(QuotasQuotadefinition, models.DO_NOTHING)


class QuotasQuotaordernumberoriginexclusion(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    excluded_geographical_area = models.ForeignKey(
        "GeoAreasGeographicalarea",
        models.DO_NOTHING,
    )
    origin = models.ForeignKey(QuotasQuotaordernumberorigin, models.DO_NOTHING)


class QuotasQuotaevent(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    subrecord_code = models.CharField(max_length=2)
    occurrence_timestamp = models.DateTimeField()
    data = models.JSONField()
    quota_definition = models.ForeignKey(QuotasQuotadefinition, models.DO_NOTHING)


class QuotasQuotablocking(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    blocking_period_type = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(QuotasQuotadefinition, models.DO_NOTHING)
