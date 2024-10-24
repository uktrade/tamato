from django.db import models
from psycopg.types.range import DateRange


class ReportCertificateType(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)


class ReportCertificateType(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(ReportCertificateType, models.DO_NOTHING)


class ReportCertificate(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.CharField(max_length=3)
    certificate_type = models.ForeignKey(
        "ReportCertificateType",
        models.DO_NOTHING,
    )


class ReportCertificate(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(ReportCertificate, models.DO_NOTHING)


class ReportCertificateDescription(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    described_certificate = models.ForeignKey(
        ReportCertificate,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()
