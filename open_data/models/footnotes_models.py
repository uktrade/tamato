# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class FootnotesFootnote(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    footnote_id = models.CharField(max_length=5)
    footnote_type = models.ForeignKey("FootnotesFootnotetype", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "footnotes_footnote"


class FootnotesFootnotetype(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    footnote_type_id = models.CharField(max_length=3)
    application_code = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "footnotes_footnotetype"


class FootnotesFootnotedescription(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    description = models.TextField(blank=True, null=True)
    sid = models.IntegerField()
    described_footnote = models.ForeignKey(FootnotesFootnote, models.DO_NOTHING)
    validity_start = models.DateField()

    class Meta:
        managed = False
        db_table = "footnotes_footnotedescription"
