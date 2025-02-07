from django.db import models

from open_data.models.utils import create_name_with_schema


class MeasureAsDefinedReport(models.Model):
    id_counter = models.IntegerField()
    trackedmodel_ptr_id = models.IntegerField(primary_key=True)
    commodity_sid = models.IntegerField(blank=True, null=True)
    commodity_code = models.CharField(max_length=10, blank=True, null=True)
    commodity_indent = models.IntegerField(blank=True, null=True)
    commodity_description = models.TextField(blank=True, null=True)
    measure_sid = models.IntegerField()
    measure_type_id = models.CharField(max_length=500, blank=True, null=True)
    measure_type_description = models.CharField(max_length=500, blank=True, null=True)
    measure_additional_code_code = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    measure_additional_code_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    measure_duty_expression = models.CharField(max_length=500, blank=True, null=True)
    measure_effective_start_date = models.DateField()
    measure_effective_end_date = models.DateField(blank=True, null=True)
    measure_reduction_indicator = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    measure_footnotes = models.TextField(blank=True, null=True)
    measure_conditions = models.CharField(max_length=500, blank=True, null=True)
    measure_geographical_area_sid = models.IntegerField(blank=True, null=True)
    measure_geographical_area_id = models.CharField(
        max_length=4,
        blank=True,
        null=True,
    )
    measure_geographical_area_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    measure_excluded_geographical_areas_ids = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    measure_excluded_geographical_areas_descriptions = models.TextField(
        blank=True,
        null=True,
    )
    measure_quota_order_number = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )
    measure_regulation_id = models.CharField(max_length=8, blank=True, null=True)
    measure_regulation_url = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = create_name_with_schema("measure_as_defined_report")
