from django.db import models
from psycopg.types.range import DateRange


class GeographicalAreaLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    area_id = models.CharField(max_length=4)
    area_code = models.SmallIntegerField()
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)


class GeographicalAreaLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(GeographicalAreaLatest, models.DO_NOTHING)


class GeographicalMembershipLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    geo_group = models.ForeignKey(GeographicalAreaLookUp, models.DO_NOTHING)
    member = models.ForeignKey(
        GeographicalAreaLookUp,
        models.DO_NOTHING,
        related_name="geoareasgeographicalmembership_member_set",
    )


class GeographicalMembershipLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(GeographicalMembershipLatest, models.DO_NOTHING)


class GeographicalareaDescriptionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    sid = models.IntegerField()
    described_geographicalarea = models.ForeignKey(
        GeographicalAreaLookUp,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class GeographicalareaDescriptionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        GeographicalareaDescriptionLatest,
        models.DO_NOTHING,
    )
