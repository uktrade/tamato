from django.db import models

from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaDefinition
from quotas.models import QuotaEvent
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.models import QuotaSuspension


class ReportQuotaAssociation(ReportModel):
    shadowed_model = QuotaAssociation

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    sub_quota_relation_type = models.CharField(max_length=2)
    coefficient = models.DecimalField(max_digits=16, decimal_places=5)
    main_quota = models.ForeignKey("ReportQuotaDefinition", models.DO_NOTHING)
    sub_quota = models.ForeignKey(
        "ReportQuotaDefinition",
        models.DO_NOTHING,
        related_name="quotasquotaassociation_sub_quota_set",
    )

    class Meta:
        db_table = ReportModel.create_table_name(QuotaAssociation)


class ReportQuotaDefinition(ReportModel):
    shadowed_model = QuotaDefinition

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    volume = models.DecimalField(max_digits=14, decimal_places=3)
    initial_volume = models.DecimalField(max_digits=14, decimal_places=3)
    maximum_precision = models.SmallIntegerField()
    quota_critical = models.BooleanField()
    quota_critical_threshold = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    measurement_unit = models.ForeignKey(
        "ReportMeasurementUnit",
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

    class Meta:
        db_table = ReportModel.create_table_name(QuotaDefinition)


class ReportQuotaOrderNumber(ReportModel):
    shadowed_model = QuotaOrderNumber

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    order_number = models.CharField(max_length=6)
    mechanism = models.SmallIntegerField()
    category = models.SmallIntegerField()

    class Meta:
        db_table = ReportModel.create_table_name(QuotaOrderNumber)


class ReportQuotaOrderNumberOrigin(ReportModel):
    shadowed_model = QuotaOrderNumberOrigin

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    geographical_area = models.ForeignKey("ReportGeographicalArea", models.DO_NOTHING)
    order_number = models.ForeignKey(ReportQuotaOrderNumber, models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(QuotaOrderNumberOrigin)


class ReportQuotaSuspension(ReportModel):
    shadowed_model = QuotaSuspension

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(ReportQuotaDefinition, models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(QuotaSuspension)


class ReportQuotaOrderNumberOriginExclusion(ReportModel):
    shadowed_model = QuotaOrderNumberOriginExclusion

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    excluded_geographical_area = models.ForeignKey(
        "ReportGeographicalArea",
        models.DO_NOTHING,
    )
    origin = models.ForeignKey(ReportQuotaOrderNumberOrigin, models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(QuotaOrderNumberOriginExclusion)


class ReportQuotaEvent(ReportModel):
    shadowed_model = QuotaEvent

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    subrecord_code = models.CharField(max_length=2)
    occurrence_timestamp = models.DateTimeField()
    data = models.JSONField()
    quota_definition = models.ForeignKey(ReportQuotaDefinition, models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(QuotaEvent)


class ReportQuotaBlocking(ReportModel):
    shadowed_model = QuotaBlocking

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    blocking_period_type = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    quota_definition = models.ForeignKey(ReportQuotaDefinition, models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(QuotaBlocking)
