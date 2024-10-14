from django.db import models
from psycopg.types.range import DateRange


class AdditionalCodeTypeMeasureType(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = models.DateRange
    additional_code_type = models.ForeignKey(
        "AdditionalCodesAdditionalcodetype",
        models.DO_NOTHING,
    )
    measure_type = models.ForeignKey("MeasuresMeasuretype", models.DO_NOTHING)


class DutyExpression(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = models.DateRange
    sid = models.IntegerField()
    prefix = models.CharField(max_length=14)
    duty_amount_applicability_code = models.SmallIntegerField()
    measurement_unit_applicability_code = models.SmallIntegerField()
    monetary_unit_applicability_code = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class FootnoteAssociationMeasure(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    associated_footnote = models.ForeignKey("FootnotesFootnote", models.DO_NOTHING)
    footnoted_measure = models.ForeignKey("MeasuresMeasure", models.DO_NOTHING)


class Measure(models.Model):
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


class MeasureAction(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    requires_duty = models.BooleanField()


class MeasureConditionComponent(models.Model):
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
    duty_expression = models.ForeignKey("MeasuresDutyexpression", models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        "MeasuresMonetaryunit",
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class MeasureCondition(models.Model):
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
    dependent_measure = models.ForeignKey(Measure, models.DO_NOTHING)
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


class MeasureConditionCode(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=2)
    description = models.CharField(max_length=500, blank=True, null=True)
    accepts_certificate = models.BooleanField()
    accepts_price = models.BooleanField()


class MeasurementUnit(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)


class MeasurementUnitQualifier(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)


class MeasureTypeSeries(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    sid = models.CharField(max_length=2)
    measure_type_combination = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)


class MonetaryUnit(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)


class MeasureType(models.Model):
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


class Measurement(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange
    measurement_unit = models.ForeignKey(MeasuresMeasurementunit, models.DO_NOTHING)
    measurement_unit_qualifier = models.ForeignKey(
        MeasuresMeasurementunitqualifier,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )


class MeasureExcludedGeographicalArea(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    excluded_geographical_area = models.ForeignKey(
        "GeoAreasGeographicalarea",
        models.DO_NOTHING,
    )
    modified_measure = models.ForeignKey(Measure, models.DO_NOTHING)


class MeasureComponent(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    component_measure = models.ForeignKey(Measure, models.DO_NOTHING)
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
