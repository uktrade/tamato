from django.db import models
from psycopg.types.range import DateRange


class GeoAreasGeographicalarea(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    area_id = models.CharField(max_length=4)
    area_code = models.SmallIntegerField()
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)


class GeoAreasGeographicalmembership(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    geo_group = models.ForeignKey(GeoAreasGeographicalarea, models.DO_NOTHING)
    member = models.ForeignKey(
        GeoAreasGeographicalarea,
        models.DO_NOTHING,
        related_name="geoareasgeographicalmembership_member_set",
    )


class GeoAreasGeographicalareadescription(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    sid = models.IntegerField()
    described_geographicalarea = models.ForeignKey(
        GeoAreasGeographicalarea,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()
