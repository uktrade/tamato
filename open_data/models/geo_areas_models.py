from django.db import models

from common.fields import TaricDateRangeField
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from open_data.models.utils import ReportModel


class ReportGeographicalArea(ReportModel):
    shadowed_model = GeographicalArea
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    area_id = models.CharField(max_length=4)
    area_code = models.SmallIntegerField()
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(GeographicalArea)


class ReportGeographicalMembership(ReportModel):
    shadowed_model = GeographicalMembership
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    geo_group = models.ForeignKey(ReportGeographicalArea, models.DO_NOTHING)
    member = models.ForeignKey(
        ReportGeographicalArea,
        models.DO_NOTHING,
        related_name="geoareasgeographicalmembership_member_set",
    )

    class Meta:
        db_table = ReportModel.create_table_name(GeographicalMembership)


class ReportGeographicalAreaDescription(ReportModel):
    shadowed_model = GeographicalAreaDescription
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    description = models.CharField(max_length=500, blank=True, null=True)
    sid = models.IntegerField()
    described_geographicalarea = models.ForeignKey(
        ReportGeographicalArea,
        models.DO_NOTHING,
        related_name="descriptions",
    )
    validity_start = models.DateField()

    class Meta:
        db_table = ReportModel.create_table_name(GeographicalAreaDescription)
