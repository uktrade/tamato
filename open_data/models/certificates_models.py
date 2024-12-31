from django.db import models

from certificates.models import Certificate
from certificates.models import CertificateDescription
from certificates.models import CertificateType
from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel


class ReportCertificateType(ReportModel):
    shadowed_model = CertificateType
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=1)
    description = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(CertificateType)


class ReportCertificate(ReportModel):
    shadowed_model = Certificate
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=3)
    certificate_type = models.ForeignKey(
        "ReportCertificateType",
        models.DO_NOTHING,
    )

    class Meta:
        db_table = ReportModel.create_table_name(Certificate)


class ReportCertificateDescription(ReportModel):
    shadowed_model = CertificateDescription
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

    class Meta:
        db_table = ReportModel.create_table_name(CertificateDescription)
