# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class CertificatesCertificate(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.CharField(max_length=3)
    certificate_type = models.ForeignKey(
        "CertificatesCertificatetype",
        models.DO_NOTHING,
    )

    class Meta:
        managed = False
        db_table = "certificates_certificate"


class CertificatesCertificatetype(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "certificates_certificatetype"


class CertificatesCertificatedescription(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    described_certificate = models.ForeignKey(
        CertificatesCertificate,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()

    class Meta:
        managed = False
        db_table = "certificates_certificatedescription"
