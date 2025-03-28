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
    commodity_validity_start = models.DateField(db_index=True, null=False, blank=False)
    commodity_validity_end = models.DateField(null=True, blank=True)
    parent_sid = models.IntegerField(blank=True, null=True)
    parent_code = models.CharField(max_length=10, blank=True, null=True)
    parent_suffix = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        db_table = create_open_data_name("commodityreport")
