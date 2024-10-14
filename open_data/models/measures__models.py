# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class MeasuresAdditionalcodetypemeasuretype(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    additional_code_type = models.ForeignKey(
        "AdditionalCodesAdditionalcodetype",
        models.DO_NOTHING,
    )
    measure_type = models.ForeignKey("MeasuresMeasuretype", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "measures_additionalcodetypemeasuretype"


class MeasuresDutyexpression(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.IntegerField()
    prefix = models.CharField(max_length=14)
    duty_amount_applicability_code = models.SmallIntegerField()
    measurement_unit_applicability_code = models.SmallIntegerField()
    monetary_unit_applicability_code = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "measures_dutyexpression"


class MeasuresFootnoteassociationmeasure(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    associated_footnote = models.ForeignKey("FootnotesFootnote", models.DO_NOTHING)
    footnoted_measure = models.ForeignKey("MeasuresMeasure", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "measures_footnoteassociationmeasure"


class MeasuresMeasure(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
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

    class Meta:
        managed = False
        db_table = "measures_measure"


class MeasuresMeasureaction(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    requires_duty = models.BooleanField()

    class Meta:
        managed = False
        db_table = "measures_measureaction"


class MeasuresMeasureconditioncomponent(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
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

    class Meta:
        managed = False
        db_table = "measures_measureconditioncomponent"


class MeasuresMeasurecondition(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
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
        MeasuresMeasureaction,
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
    dependent_measure = models.ForeignKey(MeasuresMeasure, models.DO_NOTHING)
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

    class Meta:
        managed = False
        db_table = "measures_measurecondition"


class MeasuresMeasureconditioncode(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    code = models.CharField(max_length=2)
    description = models.CharField(max_length=500, blank=True, null=True)
    accepts_certificate = models.BooleanField()
    accepts_price = models.BooleanField()

    class Meta:
        managed = False
        db_table = "measures_measureconditioncode"


class MeasuresMeasurementunit(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)

    class Meta:
        managed = False
        db_table = "measures_measurementunit"


class MeasuresMeasurementunitqualifier(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    code = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    abbreviation = models.CharField(max_length=32)

    class Meta:
        managed = False
        db_table = "measures_measurementunitqualifier"


class MeasuresMeasuretypeseries(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.CharField(max_length=2)
    measure_type_combination = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "measures_measuretypeseries"


class MeasuresMonetaryunit(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    code = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "measures_monetaryunit"


class MeasuresMeasuretype(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.CharField(max_length=6)
    trade_movement_code = models.SmallIntegerField()
    priority_code = models.SmallIntegerField()
    measure_component_applicability_code = models.SmallIntegerField()
    origin_destination_code = models.SmallIntegerField()
    order_number_capture_code = models.SmallIntegerField()
    measure_explosion_level = models.SmallIntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    measure_type_series = models.ForeignKey(
        MeasuresMeasuretypeseries,
        models.DO_NOTHING,
    )

    class Meta:
        managed = False
        db_table = "measures_measuretype"


class MeasuresMeasurement(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    measurement_unit = models.ForeignKey(MeasuresMeasurementunit, models.DO_NOTHING)
    measurement_unit_qualifier = models.ForeignKey(
        MeasuresMeasurementunitqualifier,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "measures_measurement"


class MeasuresMeasureexcludedgeographicalarea(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    excluded_geographical_area = models.ForeignKey(
        "GeoAreasGeographicalarea",
        models.DO_NOTHING,
    )
    modified_measure = models.ForeignKey(MeasuresMeasure, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "measures_measureexcludedgeographicalarea"


class MeasuresMeasurecomponent(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    duty_amount = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
    )
    component_measure = models.ForeignKey(MeasuresMeasure, models.DO_NOTHING)
    component_measurement = models.ForeignKey(
        MeasuresMeasurement,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )
    duty_expression = models.ForeignKey(MeasuresDutyexpression, models.DO_NOTHING)
    monetary_unit = models.ForeignKey(
        MeasuresMonetaryunit,
        models.DO_NOTHING,
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "measures_measurecomponent"
