from django.db import models
from django.db.models import fields
from django_fsm import FSMField

from common.models import TimestampedMixin


class ReferenceDocumentVersionStatus(models.TextChoices):
    # Reference document version can be edited
    EDITING = "EDITING", "Editing"
    # Reference document version ius locked and in review
    IN_REVIEW = "IN_REVIEW", "In Review"
    # reference document version has been approved and published
    PUBLISHED = "PUBLISHED", "Published"


class ReferenceDocument(models.Model, TimestampedMixin):
    title = models.CharField(
        max_length=255,
        help_text="Short name for this workbasket",
        db_index=True,
        unique=True,
    )

    area_id = models.CharField(
        max_length=4,
        db_index=True,
    )


class ReferenceDocumentVersion(models.Model, TimestampedMixin):
    version = models.FloatField()
    published_date = models.DateField(blank=True, null=True)
    entry_into_force_date = models.DateField(blank=True, null=True)

    reference_document = models.ForeignKey(
        "reference_documents.ReferenceDocument",
        on_delete=models.PROTECT,
        related_name="reference_document_versions",
    )
    status = FSMField(
        default=ReferenceDocumentVersionStatus.EDITING,
        choices=ReferenceDocumentVersionStatus.choices,
        db_index=True,
        protected=False,
        editable=False,
    )


class PreferentialRate(models.Model):
    commodity_code = models.CharField(
        max_length=10,
        db_index=True,
    )
    duty_rate = models.CharField(
        max_length=255,
    )
    order = models.IntegerField()

    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="preferential_rates",
    )

    valid_start_day = models.IntegerField(blank=True, null=True)
    valid_start_month = models.IntegerField(blank=True, null=True)
    valid_end_day = models.IntegerField(blank=True, null=True)
    valid_end_month = models.IntegerField(blank=True, null=True)


class PreferentialQuota(models.Model):
    quota_order_number = models.CharField(
        max_length=6,
        db_index=True,
    )
    commodity_code = models.CharField(
        max_length=10,
        db_index=True,
    )
    quota_duty_rate = models.CharField(
        max_length=255,
    )
    volume = models.CharField(
        max_length=255,
    )

    valid_start_day = models.IntegerField(blank=True, null=True)
    valid_start_month = models.IntegerField(blank=True, null=True)
    valid_end_day = models.IntegerField(blank=True, null=True)
    valid_end_month = models.IntegerField(blank=True, null=True)

    measurement = models.CharField(
        max_length=255,
    )

    order = models.IntegerField()

    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="preferential_quotas",
    )


class AlignmentReport(models.Model, TimestampedMixin):
    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="alignment_reports",
    )


class AlignmentReportCheck(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    alignment_report = models.ForeignKey(
        "reference_documents.AlignmentReport",
        on_delete=models.PROTECT,
        related_name="alignment_report_checks",
    )

    check_name = fields.CharField(max_length=255)
    """A string identifying the type of check carried out."""

    successful = fields.BooleanField()
    """True if the check was successful."""

    message = fields.TextField(null=True)
    """The text content returned by the check, if any."""

    preferential_quota = models.ForeignKey(
        "reference_documents.PreferentialQuota",
        on_delete=models.PROTECT,
        related_name="alignment_report_checks",
        blank=True,
        null=True,
    )

    preferential_rate = models.ForeignKey(
        "reference_documents.PreferentialRate",
        on_delete=models.PROTECT,
        related_name="alignment_report_checks",
        blank=True,
        null=True,
    )
