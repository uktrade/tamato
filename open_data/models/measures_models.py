from django.db import models

from common.fields import TaricDateRangeField
from measures.models.tracked_models import AdditionalCodeTypeMeasureType
from measures.models.tracked_models import DutyExpression
from measures.models.tracked_models import FootnoteAssociationMeasure
from measures.models.tracked_models import Measure
from measures.models.tracked_models import MeasureAction
from measures.models.tracked_models import MeasureComponent
from measures.models.tracked_models import MeasureCondition
from measures.models.tracked_models import MeasureConditionCode
from measures.models.tracked_models import MeasureConditionComponent
from measures.models.tracked_models import MeasureExcludedGeographicalArea
from measures.models.tracked_models import Measurement
from measures.models.tracked_models import MeasurementUnit
from measures.models.tracked_models import MeasurementUnitQualifier
from measures.models.tracked_models import MeasureType
from measures.models.tracked_models import MeasureTypeSeries
from measures.models.tracked_models import MonetaryUnit
from open_data.models.utils import ReportModel


class ReportAdditionalCodeTypeMeasureType(ReportModel):
    shadowed_model = AdditionalCodeTypeMeasureType
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

    class Meta:
        db_table = ReportModel.create_table_name(AdditionalCodeTypeMeasureType)


class ReportDutyExpression(ReportModel):
    shadowed_model = DutyExpression

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

    class Meta:
        db_table = ReportModel.create_table_name(DutyExpression)


class ReportFootnoteAssociationMeasure(ReportModel):
    shadowed_model = FootnoteAssociationMeasure

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    associated_footnote = models.ForeignKey("ReportFootnote", models.DO_NOTHING)
    footnoted_measure = models.ForeignKey("ReportMeasure", models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(FootnoteAssociationMeasure)


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
    shadowed_model = MeasureAction

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    requires_duty = models.BooleanField()

    class Meta:
        db_table = ReportModel.create_table_name(MeasureAction)


class ReportMeasureConditionComponent(ReportModel):
    shadowed_model = MeasureConditionComponent

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

    class Meta:
        db_table = ReportModel.create_table_name(MeasureConditionComponent)


class ReportMeasureCondition(ReportModel):
    shadowed_model = MeasureCondition

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

    class Meta:
        db_table = ReportModel.create_table_name(MeasureCondition)


class ReportMeasureConditionCode(ReportModel):
    shadowed_model = MeasureConditionCode

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=2)
    description = models.CharField(max_length=500, blank=True, null=True)
    accepts_certificate = models.BooleanField()
    accepts_price = models.BooleanField()

    class Meta:
        db_table = ReportModel.create_table_name(MeasureConditionCode)


class ReportMeasurementUnit(ReportModel):
    shadowed_model = MeasurementUnit

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)

    class Meta:
        db_table = ReportModel.create_table_name(MeasurementUnit)


class ReportMeasurementUnitQualifier(ReportModel):
    shadowed_model = MeasurementUnitQualifier

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)

    class Meta:
        db_table = ReportModel.create_table_name(MeasurementUnitQualifier)


class ReportMeasureTypeSeries(ReportModel):
    shadowed_model = MeasureTypeSeries

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=2)
    measure_type_combination = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(MeasureTypeSeries)


class ReportMonetaryUnit(ReportModel):
    shadowed_model = MonetaryUnit

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(MonetaryUnit)


class ReportMeasureType(ReportModel):
    shadowed_model = MeasureType

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

    class Meta:
        db_table = ReportModel.create_table_name(MeasureType)


class ReportMeasurement(ReportModel):
    shadowed_model = Measurement

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

    class Meta:
        db_table = ReportModel.create_table_name(Measurement)


class ReportMeasureExcludedGeographicalArea(ReportModel):
    shadowed_model = MeasureExcludedGeographicalArea

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    excluded_geographical_area = models.ForeignKey(
        "ReportGeographicalArea",
        models.DO_NOTHING,
    )
    modified_measure = models.ForeignKey(ReportMeasure, models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(MeasureExcludedGeographicalArea)


class ReportMeasureComponent(ReportModel):
    shadowed_model = MeasureComponent

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

    class Meta:
        db_table = ReportModel.create_table_name(MeasureComponent)
