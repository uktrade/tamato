from datetime import datetime, date

from django.db import models
from django_fsm import FSMField
from django.db.models import fields, Q
from django_fsm import FSMField, transition

from common.fields import TaricDateRangeField
from common.models import TimestampedMixin
from common.util import TaricDateRange


class ReferenceDocumentVersionStatus(models.TextChoices):
    # Reference document version can be edited
    EDITING = "EDITING", "Editing"
    # Reference document version ius locked and in review
    IN_REVIEW = "IN_REVIEW", "In Review"
    # reference document version has been approved and published
    PUBLISHED = "PUBLISHED", "Published"


class AlignmentReportCheckStatus(models.TextChoices):
    # Reference document version can be edited
    PASS = "PASS", "Passing"
    # Reference document version ius locked and in review
    FAIL = "FAIL", "Failed"
    # reference document version has been approved and published
    WARNING = "WARNING", "Warning"


class ReferenceDocument(TimestampedMixin):
    title = models.CharField(
        max_length=255,
        help_text="Short name for this reference document",
        db_index=True,
        unique=True,
    )

    area_id = models.CharField(
        max_length=4,
        db_index=True,
        unique=True,
    )

    def editable(self):
        if self.pk is None:
            return True
        return not self.reference_document_versions.filter(
            status__in=[
                ReferenceDocumentVersionStatus.IN_REVIEW,
                ReferenceDocumentVersionStatus.PUBLISHED,
            ]
        ).count() > 0

    def get_area_name_by_area_id(self):
        from geo_areas.models import GeographicalAreaDescription

        description = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea__area_id=self.area_id)
            .order_by("-validity_start")
            .first()
        )
        if description:
            return description.description
        else:
            return f"{self.area_id} (unknown description)"

    def save(self, *args, **kwargs):
        if not self.editable():
            return
        super(ReferenceDocument, self).save(*args, **kwargs)


class ReferenceDocumentVersion(TimestampedMixin):
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

    class Meta:
        # TODO: Add violation_error_message to this constraint once we have Django 4.1
        constraints = [
            models.UniqueConstraint(
                fields=["version", "reference_document"],
                name="unique_versions",
            ),
        ]

    def preferential_quotas(self):
        order_numbers = self.preferential_quota_order_numbers.all()
        return PreferentialQuota.objects.all().filter(
            preferential_quota_order_number__in=order_numbers,
        )

    def editable(self):
        return self.status == ReferenceDocumentVersionStatus.EDITING

    def save(self, force_save=False, *args, **kwargs):
        if not self.editable() and self.pk is not None and force_save is not True:
            return
        super(ReferenceDocumentVersion, self).save(*args, **kwargs)

    @transition(
        field=status,
        source=ReferenceDocumentVersionStatus.EDITING,
        target=ReferenceDocumentVersionStatus.IN_REVIEW,
        custom={"label": "Mark the reference document version for review."},
    )
    def in_review(self):
        """Reference document version ready to be reviewed."""
        return

    @transition(
        field=status,
        source=ReferenceDocumentVersionStatus.IN_REVIEW,
        target=ReferenceDocumentVersionStatus.PUBLISHED,
        custom={"label": "Mark the reference document as published."},
    )
    def published(self):
        """Reference document version has passed review and is published."""
        super(ReferenceDocumentVersion, self).save()
        return

    @transition(
        field=status,
        source=ReferenceDocumentVersionStatus.PUBLISHED,
        target=ReferenceDocumentVersionStatus.EDITING,
        custom={"label": "Mark the reference document version for review."},
    )
    def editing_from_published(self):
        """Reference document version has passed review and is published."""
        super(ReferenceDocumentVersion, self).save()
        return

    @transition(
        field=status,
        source=ReferenceDocumentVersionStatus.IN_REVIEW,
        target=ReferenceDocumentVersionStatus.EDITING,
        custom={"label": "Mark the reference document version for review."},
    )
    def editing_from_in_review(self):
        """Reference document version has passed review and is published."""
        super(ReferenceDocumentVersion, self).save()
        return


class PreferentialQuotaOrderNumber(models.Model):
    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="preferential_quota_order_numbers",
    )

    quota_order_number = models.CharField(
        max_length=6,
        db_index=True,
    )
    coefficient = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        blank=True,
        null=True,
        default=None,
    )
    main_order_number = models.ForeignKey(
        "self",
        related_name="sub_order_number",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    valid_between = TaricDateRangeField(
        db_index=True,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return f"{self.quota_order_number}"

    def save(self, *args, **kwargs):
        if not self.reference_document_version.editable():
            return
        super(PreferentialQuotaOrderNumber, self).save(*args, **kwargs)


class PreferentialQuota(models.Model):
    preferential_quota_order_number = models.ForeignKey(
        "reference_documents.PreferentialQuotaOrderNumber",
        on_delete=models.PROTECT,
        related_name="preferential_quotas",
        null=True,
        blank=True,
        default=None,
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
    valid_between = TaricDateRangeField(
        db_index=True,
        null=True,
        blank=True,
        default=None,
    )
    measurement = models.CharField(
        max_length=255,
    )

    def save(self, *args, **kwargs):
        if not self.preferential_quota_order_number.reference_document_version.editable():
            return
        super(PreferentialQuota, self).save(*args, **kwargs)

    class PreferentialQuotaSuspension(models.Model):
        preferential_quota = models.ForeignKey(
            "reference_documents.PreferentialQuota",
            on_delete=models.PROTECT,
            related_name="preferential_quota_suspensions",
        )

        valid_between = TaricDateRangeField(
            db_index=True,
            null=True,
            blank=True,
            default=None,
        )

        def save(self, *args, **kwargs):
            if not self.preferential_quota.preferential_quota_order_number.reference_document_version.editable():
                return
            super(PreferentialQuotaSuspension, self).save(*args, **kwargs)


class PreferentialQuotaTemplate(models.Model):
    preferential_quota_order_number = models.ForeignKey(
        "reference_documents.PreferentialQuotaOrderNumber",
        on_delete=models.PROTECT,
        related_name="preferential_quota_templates",
        null=True,
        blank=True,
        default=None,
    )

    commodity_code = models.CharField(max_length=10, db_index=True)
    quota_duty_rate = models.CharField(max_length=255)
    initial_volume = models.CharField(max_length=255)
    yearly_volume_increment = models.CharField(max_length=255)

    start_day = models.PositiveSmallIntegerField()
    start_month = models.PositiveSmallIntegerField()
    start_year = models.PositiveSmallIntegerField()
    end_day = models.PositiveSmallIntegerField()
    end_month = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None
    )

    measurement = models.CharField(
        max_length=255,
    )

    def dynamic_preferential_quotas(self):
        # This method will create in memory objects representing PreferentialQuotas
        # note: PreferentialQuotas will be generated up to 3 years in the future.
        # the dynamic nature of this class negates the need to create / modify records
        # once the reference document has been signed off and published (preventing further changes)

        result = []

        if not self.end_year:
            end_year = date.today().year + 3
        else:
            end_year = self.end_year

        for index, year in enumerate(range(self.start_year, end_year)):
            start_date = date(year, self.start_month, self.start_day)
            end_date = date(year, self.end_month, self.end_day)
            valid_between = TaricDateRange(start_date, end_date)
            volume_increment = 0
            if self.yearly_volume_increment:
                volume_increment = self.yearly_volume_increment

            result += PreferentialQuota(
                preferential_quota_order_number=self.preferential_quota_order_number,
                valid_between=valid_between,
                commodity_code=self.commodity_code,
                quota_duty_rate=self.quota_duty_rate,
                volume=self.initial_volume + (index * volume_increment),
                measurement=self.measurement,
            )

        return result

    def save(self, *args, **kwargs):
        if not self.preferential_quota_order_number.reference_document_version.editable():
            return
        super(PreferentialQuotaTemplate, self).save(*args, **kwargs)


class PreferentialQuotaSuspensionTemplate(models.Model):
    preferential_quota_template = models.ForeignKey(
        "reference_documents.PreferentialQuotaTemplate",
        on_delete=models.PROTECT,
        related_name="preferential_quota_suspension_templates"
    )

    start_day = models.PositiveSmallIntegerField()
    start_month = models.PositiveSmallIntegerField()
    start_year = models.PositiveSmallIntegerField()
    end_day = models.PositiveSmallIntegerField()
    end_month = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None
    )

    def dynamic_preferential_quota_suspensions(self):
        # This method will create in memory objects representing PreferentialQuotaSuspensions
        # note: PreferentialQuotaSuspensions will be generated up to 3 years in the future.
        # the dynamic nature of this class negates the need to create / modify records
        # once the reference document has been signed off and published (preventing further changes)

        result = []

        if not self.end_year:
            end_year = date.today().year + 3
        else:
            end_year = self.end_year

        for index, year in enumerate(range(self.start_year, end_year)):
            start_date = date(year, self.start_month, self.start_day)
            end_date = date(year, self.end_month, self.end_day)
            valid_between = TaricDateRange(start_date, end_date)
            volume_increment = 0
            if self.yearly_volume_increment:
                volume_increment = self.yearly_volume_increment

            result += PreferentialQuota(
                preferential_quota_order_number=self.preferential_quota_order_number,
                valid_between=valid_between,
                commodity_code=self.commodity_code,
                quota_duty_rate=self.quota_duty_rate,
                volume=self.initial_volume + (index * volume_increment),
                measurement=self.measurement,
            )

        return result

    def save(self, *args, **kwargs):
        if not self.preferential_quota_order_number.reference_document_version.editable():
            return
        super(PreferentialQuotaTemplate, self).save(*args, **kwargs)

class PreferentialRate(models.Model):
    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="preferential_rates",
        null=True,
        blank=True,
        default=None,
    )
    commodity_code = models.CharField(
        max_length=10,
        db_index=True,
    )
    duty_rate = models.CharField(
        max_length=255,
    )
    valid_between = TaricDateRangeField(
        db_index=True,
        null=True,
        blank=True,
        default=None,
    )

    def save(self, *args, **kwargs):
        if not self.reference_document_version.editable():
            return
        super(PreferentialRate, self).save(*args, **kwargs)


class AlignmentReport(TimestampedMixin):
    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="alignment_reports",
    )


class AlignmentReportCheck(TimestampedMixin):
    alignment_report = models.ForeignKey(
        "reference_documents.AlignmentReport",
        on_delete=models.PROTECT,
        related_name="alignment_report_checks",
    )

    check_name = fields.CharField(max_length=255)
    """A string identifying the type of check carried out."""

    status = FSMField(
        default=AlignmentReportCheckStatus.FAIL,
        choices=AlignmentReportCheckStatus.choices,
        db_index=True,
        protected=False,
        editable=False,
    )
    message = fields.TextField(null=True)
    """The text content returned by the check, if any."""

    preferential_quota = models.ForeignKey(
        "reference_documents.PreferentialQuota",
        on_delete=models.PROTECT,
        related_name="preferential_quota_checks",
        blank=True,
        null=True,
    )

    preferential_quota_order_number = models.ForeignKey(
        "reference_documents.PreferentialQuotaOrderNumber",
        on_delete=models.PROTECT,
        related_name="preferential_quota_order_number_checks",
        blank=True,
        null=True,
    )

    preferential_rate = models.ForeignKey(
        "reference_documents.PreferentialRate",
        on_delete=models.PROTECT,
        related_name="preferential_rate_checks",
        blank=True,
        null=True,
    )
