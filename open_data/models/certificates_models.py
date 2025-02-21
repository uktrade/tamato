from django.db import models

from certificates.models import Certificate
from certificates.models import CertificateType
from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel


class ReportCertificateType(ReportModel):
    shadowed_model = CertificateType
    trackedmodel_ptr = models.ForeignKey(
        shadowed_model,
        models.DO_NOTHING,
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
    update_description = True
    trackedmodel_ptr = models.ForeignKey(
        shadowed_model,
        models.DO_NOTHING,
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.CharField(max_length=3)
    certificate_type = models.ForeignKey(
        "ReportCertificateType",
        models.DO_NOTHING,
    )
    # Field completed using orm functions
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = ReportModel.create_table_name(Certificate)
