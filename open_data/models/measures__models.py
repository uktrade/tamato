from django.db import models
from psycopg.types.range import DateRange


class AdditionalCodeTypeMeasureTypeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = models.DateRange
    additional_code_type = models.ForeignKey(
        "AdditionalCodesAdditionalcodetype",
        models.DO_NOTHING,
    )
    measure_type = models.ForeignKey("MeasuresMeasuretype", models.DO_NOTHING)


class AdditionalCodeTypeMeasureTypeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        AdditionalCodeTypeMeasureTypeLatest,
        models.DO_NOTHING,
    )


class DutyExpressionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = models.DateRange
    sid = models.IntegerField()
    prefix = models.CharField(max_length=14)
    duty_amount_applicability_code = models.SmallIntegerField()
    measurement_unit_applicability_code = models.SmallIntegerField()
    monetary_unit_applicability_code = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class DutyExpressionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(DutyExpressionLatest, models.DO_NOTHING)


class FootnoteAssociationMeasureLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    associated_footnote = models.ForeignKey("FootnotesFootnote", models.DO_NOTHING)
    footnoted_measure = models.ForeignKey("MeasuresMeasure", models.DO_NOTHING)


class FootnoteAssociationMeasureLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        FootnoteAssociationMeasureLatest,
        models.DO_NOTHING,
    )


class MeasureLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.IntegerField()
    dead_additional_code = models.CharField(max_length=16, blank=True, null=True)
    dead_order_number = models.CharField(max_length=6, blank=True, null=True)
    reduction = models.SmallIntegerField(blank=True, null=True)
    stopped = models.BooleanField()
    export_refund_nomenclature_sid = models.IntegerField(blank=True, null=True)
    additional_code = models.ForeignKey(
        "AdditionalCodesAdditionalcode",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    generating_regulation = models.ForeignKey(
        "RegulationsRegulation",
        models.DO_NOTHING,
    )
    geographical_area = models.ForeignKey("GeoAreasGeographicalarea", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        "CommoditiesGoodsnomenclature",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    measure_type = models.ForeignKey("MeasuresMeasuretype", models.DO_NOTHING)
    order_number = models.ForeignKey(
        "QuotasQuotaordernumber",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    terminating_regulation = models.ForeignKey(
        "RegulationsRegulation",
        models.DO_NOTHING,
        related_name="measuresmeasure_terminating_regulation_set",
        blank=True,
        null=True,
    )


class MeasureLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureLatest, models.DO_NOTHING)


class MeasureActionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    requires_duty = models.BooleanField()


class MeasureActionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureActionLatest, models.DO_NOTHING)


class MeasureConditionComponentLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    condition = models.ForeignKey("MeasuresMeasurecondition", models.DO_NOTHING)
    component_measurement = models.ForeignKey(
        "MeasuresMeasurement",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    duty_expression = models.ForeignKey("DutyExpressionLatest", models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        "MeasuresMonetaryunit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class MeasureConditionComponentLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        MeasureConditionComponentLatest,
        models.DO_NOTHING,
    )


class MeasureConditionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    component_sequence_number = models.SmallIntegerField()
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    action = models.ForeignKey(
        MeasureAction,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    condition_code = models.ForeignKey(
        "MeasuresMeasureconditioncode",
        models.DO_NOTHING,
    )
    condition_measurement = models.ForeignKey(
        "MeasuresMeasurement",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    dependent_measure = models.ForeignKey(MeasureLookUp, models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        "MeasuresMonetaryunit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    required_certificate = models.ForeignKey(
        "CertificatesCertificate",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class MeasureConditionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureConditionLatest, models.DO_NOTHING)


class MeasureConditionCodeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=2)
    description = models.CharField(max_length=500, blank=True, null=True)
    accepts_certificate = models.BooleanField()
    accepts_price = models.BooleanField()


class MeasureConditionCodeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureConditionCodeLatest, models.DO_NOTHING)


class MeasurementUnitLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)


class MeasurementUnitLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasurementUnitLatest, models.DO_NOTHING)


class MeasurementUnitQualifierLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)


class MeasurementUnitQualifierLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        MeasurementUnitQualifierLatest,
        models.DO_NOTHING,
    )


class MeasureTypeSeriesLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.CharField(max_length=2)
    measure_type_combination = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class MeasureTypeSeriesLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureTypeSeriesLatest, models.DO_NOTHING)


class MonetaryUnitLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)


class MonetaryUnitLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MonetaryUnitLatest, models.DO_NOTHING)


class MeasureTypeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.CharField(max_length=6)
    trade_movement_code = models.SmallIntegerField()
    priority_code = models.SmallIntegerField()
    measure_component_applicability_code = models.SmallIntegerField()
    origin_destination_code = models.SmallIntegerField()
    order_number_capture_code = models.SmallIntegerField()
    measure_explosion_level = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    measure_type_series = models.ForeignKey(
        MeasureTypeSeries,
        models.DO_NOTHING,
    )


class MeasureTypeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureTypeLatest, models.DO_NOTHING)


class MeasurementLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    measurement_unit = models.ForeignKey(MeasuresMeasurementunit, models.DO_NOTHING)
    measurement_unit_qualifier = models.ForeignKey(
        MeasuresMeasurementunitqualifier,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class MeasurementLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasurementLatest, models.DO_NOTHING)


class MeasureExcludedGeographicalAreaLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    excluded_geographical_area = models.ForeignKey(
        "GeoAreasGeographicalarea",
        models.DO_NOTHING,
    )
    modified_measure = models.ForeignKey(Measure, models.DO_NOTHING)


class MeasureExcludedGeographicalAreaLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        MeasureExcludedGeographicalAreaLatest,
        models.DO_NOTHING,
    )


class MeasureComponentLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    component_measure = models.ForeignKey(MeasureLookUp, models.DO_NOTHING)
    component_measurement = models.ForeignKey(
        Measurement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    duty_expression = models.ForeignKey(DutyExpression, models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        MonetaryUnit,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class MeasureComponentLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(MeasureComponentLatest, models.DO_NOTHING)
