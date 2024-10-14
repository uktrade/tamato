# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class GeoAreasGeographicalarea(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.IntegerField()
    area_id = models.CharField(max_length=4)
    area_code = models.SmallIntegerField()
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "geo_areas_geographicalarea"


class GeoAreasGeographicalmembership(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    geo_group = models.ForeignKey(GeoAreasGeographicalarea, models.DO_NOTHING)
    member = models.ForeignKey(
        GeoAreasGeographicalarea,
        models.DO_NOTHING,
        related_name="geoareasgeographicalmembership_member_set",
    )

    class Meta:
        managed = False
        db_table = "geo_areas_geographicalmembership"


class GeoAreasGeographicalareadescription(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    description = models.CharField(max_length=500, blank=True, null=True)
    sid = models.IntegerField()
    described_geographicalarea = models.ForeignKey(
        GeoAreasGeographicalarea,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()

    class Meta:
        managed = False
        db_table = "geo_areas_geographicalareadescription"
