from django.db import models
from psycopg.types.range import DateRange


class CertificateTypeLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)


class CertificateTypeLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(CertificateTypeLatest, models.DO_NOTHING)


class CertificateLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.CharField(max_length=3)
    certificate_type = models.ForeignKey(
        "CertificatetypeLookUp",
        models.DO_NOTHING,
    )


class CertificateLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(CertificateLatest, models.DO_NOTHING)


class CertificateDescriptionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    described_certificate = models.ForeignKey(
        CertificateLookUp,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class CertificateDescriptionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(CertificateDescriptionLatest, models.DO_NOTHING)
