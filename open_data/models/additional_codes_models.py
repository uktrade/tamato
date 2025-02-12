from django.db import models

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel


class ReportAdditionalCodeType(ReportModel):
    shadowed_model = AdditionalCodeType
    trackedmodel_ptr = models.OneToOneField(
        shadowed_model,
        models.DO_NOTHING,
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )

    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)
    application_code = models.SmallIntegerField()

    class Meta:
        db_table = ReportModel.create_table_name(AdditionalCodeType)


class ReportAdditionalCode(ReportModel):
    shadowed_model = AdditionalCode
    update_description = True
    trackedmodel_ptr = models.OneToOneField(
        shadowed_model,
        models.DO_NOTHING,
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )

    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    code = models.CharField(max_length=3)
    type = models.ForeignKey(ReportAdditionalCodeType, models.DO_NOTHING)
    # Field completed using orm functions
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(AdditionalCode)
