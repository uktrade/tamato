from django.db import models

from common.fields import TaricDateRangeField


class ReportCertificateType(models.Model):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)()
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)


class ReportCertificate(models.Model):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)()
    sid = models.CharField(max_length=3)
    certificate_type = models.ForeignKey(
        "ReportCertificateType",
        models.DO_NOTHING,
    )


class ReportCertificateDescription(models.Model):
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    sid = models.IntegerField()
    description = models.CharField(max_length=500, blank=True, null=True)
    described_certificate = models.ForeignKey(
        ReportCertificate,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()
