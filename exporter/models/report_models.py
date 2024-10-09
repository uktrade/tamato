from django.db import models


class ExportMeasure(models.Model):
    """Maps to the database view returning the fileds required for exporting
    Measures."""

    trackedmodel_ptr_id = models.PositiveIntegerField(
        primary_key=True,  # defined to stop Django adding an ID that does not exist in the view
        unique=False,  # no unique field  in the mapped query
        default=None,
        blank=True,
    )
    commodity_sid = models.PositiveIntegerField()
    commodity_code = models.CharField(max_length=500, null=True, blank=True)
    commodity_indent = models.CharField(max_length=500, null=True, blank=True)
    commodity_description = models.CharField(max_length=500, null=True, blank=True)
    measure_sid = models.PositiveIntegerField()
    measure_type_id = models.PositiveIntegerField()
    measure_type_description = models.CharField(max_length=500, null=True, blank=True)
    measure_additional_code_code = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    measure_additional_code_description = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    measure_duty_expression = models.CharField(max_length=500, null=True, blank=True)
    measure_effective_start_date = models.DateField(null=True)
    measure_effective_end_date = models.DateField(null=True)
    measure_reduction_indicator = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    measure_footnotes = models.CharField(max_length=500, null=True, blank=True)
    measure_conditions = models.CharField(max_length=500, null=True, blank=True)
    measure_geographical_area_sid = models.PositiveIntegerField()
    measure_geographical_area_id = models.PositiveIntegerField()
    measure_geographical_area_description = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    measure_excluded_geographical_areas_ids = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    measure_excluded_geographical_areas_descriptions = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    measure_quota_order_number = models.CharField(max_length=500, null=True, blank=True)
    measure_regulation_id = models.PositiveIntegerField()
    measure_regulation_url = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "exporter_active_measures"
