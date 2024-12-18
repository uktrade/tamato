from django.db import models

from common.fields import TaricDateRangeField
from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from footnotes.models import FootnoteType
from open_data.models.utils import ReportModel


class ReportFootnoteType(ReportModel):
    shadowed_model = FootnoteType

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    footnote_type_id = models.CharField(max_length=3)
    application_code = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(FootnoteType)


class ReportFootnote(ReportModel):
    shadowed_model = Footnote

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    footnote_id = models.CharField(max_length=5)
    footnote_type = models.ForeignKey("ReportFootnoteType", models.DO_NOTHING)

    class Meta:
        db_table = ReportModel.create_table_name(Footnote)


class ReportFootnoteDescription(ReportModel):
    shadowed_model = FootnoteDescription

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    description = models.TextField(blank=True, null=True)
    sid = models.IntegerField()
    described_footnote = models.ForeignKey(ReportFootnote, models.DO_NOTHING)
    validity_start = models.DateField()

    class Meta:
        db_table = ReportModel.create_table_name(FootnoteDescription)
