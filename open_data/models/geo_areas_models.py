from django.db import models

from common.fields import TaricDateRangeField
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from open_data.models.utils import ReportModel


class ReportGeographicalArea(ReportModel):
    shadowed_model = GeographicalArea
    trackedmodel_ptr = models.OneToOneField(
        shadowed_model,
        models.DO_NOTHING,
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )

    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    area_id = models.CharField(max_length=4)
    area_code = models.SmallIntegerField()
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)

    # Field completed using orm functions
    description = models.CharField(max_length=500, blank=True, null=True)
    is_single_region_or_country = models.BooleanField(blank=True, null=True)
    is_all_countries = models.BooleanField(blank=True, null=True)
    is_group = models.BooleanField(blank=True, null=True)
    is_all_countries = models.BooleanField(blank=True, null=True)


class ReportGeographicalMembership(ReportModel):
    shadowed_model = GeographicalMembership
    trackedmodel_ptr = models.OneToOneField(
        shadowed_model,
        models.DO_NOTHING,
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
