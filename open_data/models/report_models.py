from django.db import models

from open_data.models.utils import create_open_data_name


class ReportCommodityReport(models.Model):
    # It represents the commodity report, as stored on Data Workspace
    # The model is populated when the open data is refresh
    # Using a mdel so it can easily be included in the sqlite export
    # The column names match the current report in Data Workspace
    # Confusing, because the column names of other tables are translated
    # inside Dataworkspace, but it is convenient to use the final names here

    id = models.IntegerField(
        primary_key=True,
        unique=False,
        default=None,
    )
    commodity_sid = models.IntegerField()
    commodity_code = models.CharField(max_length=10, blank=True, null=True)
    commodity_suffix = models.CharField(max_length=2, blank=True, null=True)
    commodity_description = models.TextField(blank=True, null=True)
    commodity_validity_start = models.DateField(null=False, blank=False)
    commodity_validity_end = models.DateField(null=True, blank=True)
    parent_sid = models.IntegerField(blank=True, null=True)
    parent_code = models.CharField(max_length=10, blank=True, null=True)
    parent_suffix = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        db_table = create_open_data_name("commodityreport")


class ReportMeasureAsDefinedReport(models.Model):
    # It represents the Measure As Defined report, as stored on Data Workspace
    # The model is populated when the open data is refresh
    # Using a mdel so it can easily be included in the sqlite export
    # The column names match the current report in Data Workspace
    # Confusing, because the column names of other tables are translated
    # inside Dataworkspace, but it is convenient to use the final names here

    id = models.IntegerField(
        primary_key=True,
        unique=False,
        default=None,
    )
    trackedmodel_ptr_id = models.IntegerField()
    commodity_sid = models.IntegerField(blank=True)
    commodity_code = models.CharField(max_length=10, blank=True, null=True)
    commodity_indent = models.IntegerField(null=True)
    commodity_description = models.TextField(blank=True, null=True)
    measure_sid = models.IntegerField(blank=True)
    measure_type_id = models.CharField(max_length=6)
    measure_type_description = models.TextField(blank=True, null=True)
    measure_additional_code_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )
    measure_additional_code_description = models.TextField(blank=True, null=True)
    measure_duty_expression = models.TextField(null=True, blank=True)
    measure_effective_start_date = models.DateField(null=False, blank=False)
    measure_effective_end_date = models.DateField(null=True, blank=True)
    measure_reduction_indicator = models.SmallIntegerField(blank=True, null=True)
    measure_footnotes = models.TextField(null=True, blank=True)
    measure_conditions = models.TextField(null=True, blank=True)
    measure_geographical_area_sid = models.IntegerField(null=True)
    measure_geographical_area_id = models.CharField(max_length=4)
    measure_geographical_area_description = models.TextField(blank=True, null=True)
    measure_excluded_geographical_areas_ids = models.TextField(blank=True, null=True)
    measure_excluded_geographical_areas_descriptions = models.TextField(
        blank=True,
        null=True,
    )
    measure_quota_order_number = models.CharField(max_length=50, blank=True, null=True)
    measure_regulation_id = models.CharField(max_length=50, blank=True, null=True)
    measure_regulation_url = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = create_open_data_name("measureasdefinedreport")
