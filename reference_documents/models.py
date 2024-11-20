from datetime import date

from django.db import models
from django.db.models import fields
from django_fsm import FSMField
from django_fsm import transition

from common.fields import TaricDateRangeField
from common.models import TimestampedMixin
from common.util import TaricDateRange
from quotas import validators


class ReferenceDocumentVersionStatus(models.TextChoices):
    """Choices for reference document state."""

    # Reference document version can be edited
    EDITING = "EDITING", "Editing"
    # Reference document version ius locked and in review
    IN_REVIEW = "IN_REVIEW", "In Review"
    # reference document version has been approved and published
    PUBLISHED = "PUBLISHED", "Published"


class AlignmentReportCheckStatus(models.TextChoices):
    """Choices for alignment report check state."""

    # Check passed
    PASS = "PASS", "Passing"
    # Check failed
    FAIL = "FAIL", "Failed"
    # check passed with warning
    WARNING = "WARNING", "Warning"
    # check skipped, due top parent check failing
    SKIPPED = "SKIPPED", "Skipped"


class AlignmentReportStatus(models.TextChoices):
    """Choices for alignment report state."""

    # The check has not started and is queued
    PENDING = "PENDING", "Pending"
    # the check is in progress, and currently running
    PROCESSING = "PROCESSING", "Processing"
    # The check has completed
    COMPLETE = "COMPLETE", "Complete"
    # The check unexpectedly errored during processing
    ERRORED = "ERRORED", "Errored"


class ReferenceDocument(TimestampedMixin):
    """
    This model represents a reference document, a container / parent for
    versions.

    this model holds generic information that will be used across all versions.
    This includes the geographical area, title and associated regulations.
    """

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

    regulations = models.TextField(
        help_text="List of regulation ids",
        blank=True,
        null=True,
        default=None,
    )

    def editable(self):
        """
        Indicates if this reference document is editable. It should only be
        editable when no reference document versions are published or in review.

        Returns:
            boolean: True if editable, else False
        """
        if self.pk is None:
            return True
        return (
            not self.reference_document_versions.filter(
                status__in=[
                    ReferenceDocumentVersionStatus.IN_REVIEW,
                    ReferenceDocumentVersionStatus.PUBLISHED,
                ],
            ).count()
            > 0
        )

    def get_area_name_by_area_id(self):
        """
        Looks up using data from TAP and returns a Geographical Area description
        (string)

        Returns:
            string: geographical area description or unknown (if no match)
        """
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
        """
        Saves changes to the reference document if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if self.editable():
            super(ReferenceDocument, self).save(*args, **kwargs)


class ReferenceDocumentVersion(TimestampedMixin):
    """This models represents a reference document version."""

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
        constraints = [
            models.UniqueConstraint(
                fields=["version", "reference_document"],
                name="unique_versions",
            ),
        ]

    def ref_quota_definitions(self):
        """
        Collects all RefQuotaDefinitions associated with an instance of a
        reference document version.

        Returns:
            QuerySet: query result of quota definitions
        """
        order_numbers = self.ref_order_numbers.all()
        return RefQuotaDefinition.objects.all().filter(
            ref_order_number__in=order_numbers,
        )

    def editable(self):
        """
        Indicates if this reference document version is editable.

        Returns:
            boolean: True if editable, else False
        """
        return self.status == ReferenceDocumentVersionStatus.EDITING

    def checkable(self):
        """
        Indicates if this reference document version is check-able, as in able
        have alignment checks ran against it.

        Returns:
            boolean: True if check-able, else False
        """
        return self.status == ReferenceDocumentVersionStatus.PUBLISHED

    def save(self, force_save=False, *args, **kwargs):
        """
        Saves changes to the reference document version if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if (self.editable() or force_save is True) or self.pk is None:
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
        """Reference document version is published and needs to transition to
        editable."""
        super(ReferenceDocumentVersion, self).save()
        return

    @transition(
        field=status,
        source=ReferenceDocumentVersionStatus.IN_REVIEW,
        target=ReferenceDocumentVersionStatus.EDITING,
        custom={"label": "Mark the reference document version for review."},
    )
    def editing_from_in_review(self):
        """Reference document version is in review and needs to transition to
        editable."""
        super(ReferenceDocumentVersion, self).save()
        return

    def ref_rate_count(self):
        """
        Counts the number of RefRates.

        Returns:
            int: count of RefRate entries for this reference document version
        """
        return self.ref_rates.count()

    def ref_order_number_count(self):
        """
        Counts the number of RefOrderNumbers.

        Returns:
            int: count of RefOrderNumber entries for this reference document version
        """
        return self.ref_order_numbers.count()

    def ref_quota_count(self):
        """
        Counts the number of RefQuotaDefinitions.

        Returns:
            int: count of RefQuotaDefinitions entries for this reference document version
        """
        quota_count = (
            RefQuotaDefinition.objects.all()
            .filter(
                ref_order_number__reference_document_version=self,
            )
            .count()
        )

        for quota_definition_range in RefQuotaDefinitionRange.objects.all().filter(
            ref_order_number__reference_document_version=self,
        ):
            quota_count += len(quota_definition_range.dynamic_quota_definitions())

        return quota_count

    def ref_quota_suspension_count(self):
        """
        Counts the number of RefQuotaSuspensions.

        Returns:
            int: count of RefQuotaSuspensions entries for this reference document version
        """
        suspension_count = (
            RefQuotaSuspension.objects.all()
            .filter(
                ref_quota_definition__ref_order_number__reference_document_version=self,
            )
            .count()
        )

        for quota_suspension_range in RefQuotaSuspensionRange.objects.all().filter(
            ref_quota_definition_range__ref_order_number__reference_document_version=self,
        ):
            suspension_count += len(quota_suspension_range.dynamic_quota_suspensions())

        return suspension_count


class RefOrderNumber(models.Model):
    """This model represents an order number as defined in a reference
    document."""

    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="ref_order_numbers",
    )

    order_number = models.CharField(
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
    relation_type = models.CharField(
        max_length=2,
        choices=validators.SubQuotaType.choices,
    )

    def __str__(self):
        """
        String representation if the order number.

        Returns:
            string: string representing the RefOrderNumber
        """
        return f"{self.order_number}"

    def is_sub_quota(self):
        """
        Returns a boolean representing its sub_quota status.

        Returns:
            boolean: True if it is a sub-quota of a main quota definition, else False
        """
        return self.main_order_number is not None

    def save(self, *args, **kwargs):
        """
        Saves changes to the RefOrderNumber if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if self.reference_document_version.editable():
            super(RefOrderNumber, self).save(*args, **kwargs)


class RefQuotaDefinition(models.Model):
    """
    This model represents a quota definition based on the definition from a
    reference document.

    Note: this model unlike the TAP equivalent holds the commodity_code directly. Since this is defined
    in the same way in a reference document. When querying TAP for the same data it will involve looking up the associated measures from the order number.
    """

    def __str__(self):
        return f"{self.ref_order_number.order_number} ({self.commodity_code}) {self.valid_between} {self.volume} {self.measurement}"

    ref_order_number = models.ForeignKey(
        "reference_documents.RefOrderNumber",
        on_delete=models.PROTECT,
        related_name="ref_quota_definitions",
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
        """
        Saves changes to the RefQuotaDefinition if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if not self.ref_order_number.reference_document_version.editable():
            return
        super(RefQuotaDefinition, self).save(*args, **kwargs)


class RefQuotaSuspension(models.Model):
    """This model represents a quota suspension as defined in a reference
    document."""

    ref_quota_definition = models.ForeignKey(
        "reference_documents.RefQuotaDefinition",
        on_delete=models.PROTECT,
        related_name="ref_quota_suspensions",
    )

    valid_between = TaricDateRangeField(
        db_index=True,
        null=True,
        blank=True,
        default=None,
    )

    def save(self, *args, **kwargs):
        """
        Saves changes to the RefQuotaSuspension if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if (
            self.ref_quota_definition.ref_order_number.reference_document_version.editable()
        ):
            super(RefQuotaSuspension, self).save(*args, **kwargs)


class RefQuotaDefinitionRange(models.Model):
    """This model represents a related range of quota definitions over multiple
    years."""

    def __str__(self):
        from_str = f"{self.start_day}/{self.start_month}"
        to_str = f"{self.end_day}/{self.end_month}"
        year_range = f"{self.start_year} - {self.end_year}"

        return f"{self.ref_order_number.order_number} ({self.commodity_code}) yearly range: {from_str} : {to_str} for {year_range} {self.initial_volume} {self.measurement}, increment : {self.yearly_volume_increment}"

    ref_order_number = models.ForeignKey(
        "reference_documents.RefOrderNumber",
        on_delete=models.PROTECT,
        related_name="ref_quota_definition_ranges",
        null=True,
        blank=True,
        default=None,
    )

    commodity_code = models.CharField(max_length=10, db_index=True)
    duty_rate = models.CharField(max_length=255)
    initial_volume = models.IntegerField()
    yearly_volume_increment = models.IntegerField(
        null=True,
        blank=True,
        default=None,
    )
    yearly_volume_increment_text = models.TextField()
    start_day = models.PositiveSmallIntegerField()
    start_month = models.PositiveSmallIntegerField()
    start_year = models.PositiveSmallIntegerField()
    end_day = models.PositiveSmallIntegerField()
    end_month = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    measurement = models.CharField(
        max_length=255,
    )

    def date_ranges(self):
        """
        Collects the date ranges that are covered by the RefQuotaDefinitionRange
        based on its attributes.

        Returns:
            list(TaricDateRange): A list of TaricDateRange objects
        """
        date_ranges = []

        if not self.end_year:
            end_year = date.today().year + 3
        else:
            if self.end_year > (date.today().year + 3):
                end_year = date.today().year + 3
            else:
                end_year = self.end_year

        for index, year in enumerate(range(self.start_year, end_year + 1)):
            start_date = date(year, self.start_month, self.start_day)
            end_date = date(year, self.end_month, self.end_day)
            valid_between = TaricDateRange(start_date, end_date)
            date_ranges.append(valid_between)

        return date_ranges

    def dynamic_quota_definitions(self):
        """
        A list of RefQuotaDefinitions for the range.

        note: PreferentialQuotas will be generated up to 3 years in the future.

        note: The dynamic nature of this class negates the need to create / modify records
            once the reference document has been signed off and published (preventing
            further changes)

        Returns:
            list(RefQuotaDefinition): A list of RefQuotaDefinition objects, not committed
            to the database but held in memory
        """
        # This method will create in memory objects representing PreferentialQuotas
        #
        result = []

        for index, valid_between in enumerate(self.date_ranges()):
            volume_increment = 0

            if self.yearly_volume_increment:
                volume_increment = self.yearly_volume_increment

            result.append(
                RefQuotaDefinition(
                    ref_order_number=self.ref_order_number,
                    valid_between=valid_between,
                    commodity_code=self.commodity_code,
                    duty_rate=self.duty_rate,
                    volume=int(self.initial_volume) + (index * int(volume_increment)),
                    measurement=self.measurement,
                ),
            )

        return result

    def save(self, *args, **kwargs):
        """
        Saves changes to the RefQuotaDefinitionRange if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if not self.ref_order_number.reference_document_version.editable():
            return
        super(RefQuotaDefinitionRange, self).save(*args, **kwargs)


class RefQuotaSuspensionRange(models.Model):
    """This model represents a related range of quota suspensions over multiple
    years."""

    ref_quota_definition_range = models.ForeignKey(
        "reference_documents.RefQuotaDefinitionRange",
        on_delete=models.PROTECT,
        related_name="ref_quota_suspension_ranges",
    )

    start_day = models.PositiveSmallIntegerField()
    start_month = models.PositiveSmallIntegerField()
    start_year = models.PositiveSmallIntegerField()
    end_day = models.PositiveSmallIntegerField()
    end_month = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    def date_ranges(self):
        """
        Collects the date ranges that are covered by the RefQuotaSuspensionRange
        based on its attributes.

        Returns:
            list(TaricDateRange): A list of TaricDateRange objects
        """
        date_ranges = []

        if not self.end_year:
            end_year = date.today().year + 3
        else:
            if self.end_year > (date.today().year + 3):
                end_year = date.today().year + 3
            else:
                end_year = self.end_year

        for index, year in enumerate(range(self.start_year, end_year + 1)):
            start_date = date(year, self.start_month, self.start_day)
            end_date = date(year, self.end_month, self.end_day)
            valid_between = TaricDateRange(start_date, end_date)
            date_ranges.append(valid_between)

        return date_ranges

    def dynamic_quota_suspensions(self):
        """
        A list of RefQuotaSuspensions for the range.

        note: RefQuotaSuspensions will be generated up to 3 years in the future.

        note: The dynamic nature of this class negates the need to create / modify records
            once the reference document has been signed off and published (preventing
            further changes)

        Returns:
            list(RefQuotaSuspension): A list of RefQuotaSuspension objects, not committed
            to the database but held in memory
        """
        result = []

        preferential_quotas = (
            self.ref_quota_definition_range.dynamic_quota_definitions()
        )

        for index, valid_between in enumerate(self.date_ranges()):
            # match preferential_quotas based on date range
            matched_quota = None
            for quota in preferential_quotas:
                if quota.valid_between.contains(valid_between):
                    matched_quota = quota
                    continue

            if matched_quota:
                result.append(
                    RefQuotaSuspension(
                        ref_quota_definition=matched_quota,
                        valid_between=valid_between,
                    ),
                )

        return result

    def save(self, *args, **kwargs):
        """
        Saves changes to the RefQuotaSuspensionRange if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if (
            not self.ref_quota_definition_range.ref_order_number.reference_document_version.editable()
        ):
            return
        super(RefQuotaSuspensionRange, self).save(*args, **kwargs)


class RefRate(models.Model):
    """This model represents a preferential rate."""

    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="ref_rates",
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
        """
        Saves changes to the RefRate if in an editable state.

        Args:
            *args: arguments passed to super
            **kwargs: keyword arguments passed to super

        Returns:
            None
        """
        if not self.reference_document_version.editable():
            return
        super(RefRate, self).save(*args, **kwargs)


class AlignmentReport(TimestampedMixin):
    """This model represents an alignment report, a container for checks ran
    against TAP data for a reference document."""

    reference_document_version = models.ForeignKey(
        "reference_documents.ReferenceDocumentVersion",
        on_delete=models.PROTECT,
        related_name="alignment_reports",
    )

    status = FSMField(
        default=AlignmentReportStatus.PENDING,
        choices=AlignmentReportStatus.choices,
        db_index=True,
        protected=False,
        editable=False,
    )

    @transition(
        field=status,
        source=AlignmentReportStatus.PENDING,
        target=AlignmentReportStatus.PROCESSING,
        custom={"label": "Mark the alignment check as being processed."},
    )
    def in_processing(self):
        """The alignment check has started processing."""
        return

    @transition(
        field=status,
        source=AlignmentReportStatus.PROCESSING,
        target=AlignmentReportStatus.COMPLETE,
        custom={"label": "Mark the alignment check as complete."},
    )
    def complete(self):
        """The alignment check has completed."""
        return

    @transition(
        field=status,
        source=AlignmentReportStatus.PROCESSING,
        target=AlignmentReportStatus.ERRORED,
        custom={"label": "Mark the alignment check failed with errors."},
    )
    def errored(self):
        """The alignment check has errored during execution."""
        return

    def unique_check_names(self):
        """
        Collect all unique check names associated with the AlignmentReport.

        Returns:
            list(str): a list of unique check names
        """
        return self.alignment_report_checks.distinct("check_name").values_list(
            "check_name",
            flat=True,
        )

    def check_stats(self):
        """
        Returns statistical data for the unique checks performed.

        Returns:
            dict: dictionary of statistics for check status grouped by check name
        """
        stats = {}

        for check_name in self.unique_check_names():
            stats[check_name] = {
                "total": self.alignment_report_checks.filter(
                    check_name=check_name,
                ).count(),
                "failed": self.alignment_report_checks.filter(
                    check_name=check_name,
                    status=AlignmentReportCheckStatus.FAIL,
                ).count(),
                "passed": self.alignment_report_checks.filter(
                    check_name=check_name,
                    status=AlignmentReportCheckStatus.PASS,
                ).count(),
                "warning": self.alignment_report_checks.filter(
                    check_name=check_name,
                    status=AlignmentReportCheckStatus.WARNING,
                ).count(),
                "skipped": self.alignment_report_checks.filter(
                    check_name=check_name,
                    status=AlignmentReportCheckStatus.SKIPPED,
                ).count(),
            }

        return stats

    def error_count(self):
        """
        Returns a count of errors for the AlignmentReport.

        Returns:
            int: number of errors
        """
        return self.alignment_report_checks.filter(
            status=AlignmentReportCheckStatus.FAIL,
        ).count()

    def warning_count(self):
        """
        Returns a count of warnings for the AlignmentReport.

        Returns:
           int: number of warnings
        """
        return self.alignment_report_checks.filter(
            status=AlignmentReportCheckStatus.WARNING,
        ).count()


class AlignmentReportCheck(TimestampedMixin):
    """This model represents an alignment report check, ran against TAP data for
    a single record of the reference document."""

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

    ref_quota_definition = models.ForeignKey(
        "reference_documents.RefQuotaDefinition",
        on_delete=models.PROTECT,
        related_name="ref_quota_definition_checks",
        blank=True,
        null=True,
    )

    ref_order_number = models.ForeignKey(
        "reference_documents.RefOrderNumber",
        on_delete=models.PROTECT,
        related_name="ref_order_number_checks",
        blank=True,
        null=True,
    )

    ref_rate = models.ForeignKey(
        "reference_documents.RefRate",
        on_delete=models.PROTECT,
        related_name="ref_rate_checks",
        blank=True,
        null=True,
    )

    ref_quota_definition_range = models.ForeignKey(
        "reference_documents.RefQuotaDefinitionRange",
        on_delete=models.PROTECT,
        related_name="ref_quota_definition_range_checks",
        blank=True,
        null=True,
    )

    ref_quota_suspension = models.ForeignKey(
        "reference_documents.RefQuotaSuspension",
        on_delete=models.PROTECT,
        related_name="ref_quota_suspension_checks",
        blank=True,
        null=True,
    )

    ref_quota_suspension_range = models.ForeignKey(
        "reference_documents.RefQuotaSuspensionRange",
        on_delete=models.PROTECT,
        related_name="ref_quota_suspension_range_checks",
        blank=True,
        null=True,
    )
