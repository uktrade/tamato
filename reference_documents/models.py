from django.db import models
from django_fsm import FSMField


class ReferenceDocumentVersionStatus(models.TextChoices):
    # Reference document version can be edited
    EDITING = "EDITING", "Editing"
    # Reference document version ius locked and in review
    IN_REVIEW = "IN_REVIEW", "In Review"
    # reference document version has been approved and published
    PUBLISHED = "PUBLISHED", "Published"


class ReferenceDocument(models.Model):
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


class ReferenceDocumentVersion(models.Model):
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
