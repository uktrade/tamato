from django.db import models

from additional_codes.models import AdditionalCodeType
from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel


class ReportAdditionalCodeType(ReportModel):
    shadowed_model = AdditionalCodeType
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    application_code = models.SmallIntegerField()

    class Meta:
        db_table = ReportModel.create_table_name(AdditionalCodeType)


#
# class ReportAdditionalCode(ReportModel):
#     trackedmodel_ptr = models.IntegerField(
#         primary_key=True,
#         db_column="trackedmodel_ptr_id",
#     )
#     valid_between = TaricDateRangeField(db_index=True)
#     sid = models.IntegerField()
#     code = models.CharField(max_length=3)
#     type = models.ForeignKey(ReportAdditionalCodeType, models.DO_NOTHING)
#
#     class Meta:
#         db_table = "TempName"
#
#
# class ReportAdditionalCodeDescription(ReportModel):
#     trackedmodel_ptr = models.IntegerField(
#         primary_key=True,
#         db_column="trackedmodel_ptr_id",
#     )
#     sid = models.IntegerField()
#     description = models.TextField(blank=True, null=True)
#     described_additionalcode = models.ForeignKey(
#         ReportAdditionalCode,
#         models.DO_NOTHING,
#     )
#     validity_start = models.DateField()
