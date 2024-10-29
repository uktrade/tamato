from django.db import models

from common.fields import TaricDateRangeField
from measures.models.tracked_models import Measure
from open_data.models.utils import ReportModel


class ReportAdditionalCodeTypeMeasureType(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    additional_code_type = models.ForeignKey(
        "ReportAdditionalCodeType",
        models.DO_NOTHING,
    )
    measure_type = models.ForeignKey("ReportMeasureType", models.DO_NOTHING)


class ReportDutyExpression(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    prefix = models.CharField(max_length=14)
    duty_amount_applicability_code = models.SmallIntegerField()
    measurement_unit_applicability_code = models.SmallIntegerField()
    monetary_unit_applicability_code = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class ReportFootnoteAssociationMeasure(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    associated_footnote = models.ForeignKey("ReportFootnote", models.DO_NOTHING)
    footnoted_measure = models.ForeignKey("ReportMeasure", models.DO_NOTHING)


class ReportMeasure(ReportModel):
    shadowed_model = Measure
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    dead_additional_code = models.CharField(max_length=16, blank=True, null=True)
    dead_order_number = models.CharField(max_length=6, blank=True, null=True)
    reduction = models.SmallIntegerField(blank=True, null=True)
    stopped = models.BooleanField()
    export_refund_nomenclature_sid = models.IntegerField(blank=True, null=True)
    additional_code = models.ForeignKey(
        "ReportAdditionalCode",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    generating_regulation = models.ForeignKey(
        "ReportRegulation",
        models.DO_NOTHING,
    )
    geographical_area = models.ForeignKey("ReportGeographicalArea", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        "ReportGoodsNomenclature",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    measure_type = models.ForeignKey("ReportMeasureType", models.DO_NOTHING)
    order_number = models.ForeignKey(
        "ReportQuotaOrderNumber",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    terminating_regulation = models.ForeignKey(
        "ReportRegulation",
        models.DO_NOTHING,
        related_name="measuresmeasure_terminating_regulation_set",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = ReportModel.create_table_name(Measure)


class ReportMeasureAction(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    requires_duty = models.BooleanField()


class ReportMeasureConditionComponent(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    condition = models.ForeignKey("ReportMeasureCondition", models.DO_NOTHING)
    component_measurement = models.ForeignKey(
        "ReportMeasurement",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    duty_expression = models.ForeignKey("ReportDutyExpression", models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        "ReportMonetaryUnit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class ReportMeasureCondition(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    sid = models.IntegerField()
    component_sequence_number = models.SmallIntegerField()
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    action = models.ForeignKey(
        ReportMeasureAction,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    condition_code = models.ForeignKey(
        "ReportMeasureConditionCode",
        models.DO_NOTHING,
    )
    condition_measurement = models.ForeignKey(
        "ReportMeasurement",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    dependent_measure = models.ForeignKey(ReportMeasure, models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        "ReportMonetaryUnit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    required_certificate = models.ForeignKey(
        "ReportCertificate",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class ReportMeasureConditionCode(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=2)
    description = models.CharField(max_length=500, blank=True, null=True)
    accepts_certificate = models.BooleanField()
    accepts_price = models.BooleanField()


class ReportMeasurementUnit(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)


class ReportMeasurementUnitQualifier(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)


class ReportMeasureTypeSeries(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=2)
    measure_type_combination = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class ReportMonetaryUnit(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)


class ReportMeasureType(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=6)
    trade_movement_code = models.SmallIntegerField()
    priority_code = models.SmallIntegerField()
    measure_component_applicability_code = models.SmallIntegerField()
    origin_destination_code = models.SmallIntegerField()
    order_number_capture_code = models.SmallIntegerField()
    measure_explosion_level = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    measure_type_series = models.ForeignKey(
        ReportMeasureTypeSeries,
        models.DO_NOTHING,
    )


class ReportMeasurement(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    measurement_unit = models.ForeignKey(ReportMeasurementUnit, models.DO_NOTHING)
    measurement_unit_qualifier = models.ForeignKey(
        ReportMeasurementUnitQualifier,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class ReportMeasureExcludedGeographicalArea(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    excluded_geographical_area = models.ForeignKey(
        "ReportGeographicalArea",
        models.DO_NOTHING,
    )
    modified_measure = models.ForeignKey(ReportMeasure, models.DO_NOTHING)


class ReportMeasureComponent(ReportModel):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    component_measure = models.ForeignKey(ReportMeasure, models.DO_NOTHING)
    component_measurement = models.ForeignKey(
        ReportMeasurement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    duty_expression = models.ForeignKey(ReportDutyExpression, models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        ReportMonetaryUnit,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
