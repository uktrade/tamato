from logging import getLogger

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models import QuerySet
from django_chunk_upload_handlers.clam_av import validate_virus_check_result
from django_fsm import FSMField
from django_fsm import transition

from common import validators
from common.models import TimestampedMixin
from importer.storages import CommodityImporterStorage
from importer.validators import ImportIssueType
from taric_parsers.importer_issue import ImportIssueReportItem
from workbaskets.util import clear_workbasket
from workbaskets.validators import WorkflowStatus

logger = getLogger(__name__)


class ImporterChunkStatus(models.IntegerChoices):
    WAITING = 1, "Waiting"
    RUNNING = 2, "Running"
    DONE = 3, "Done"
    ERRORED = 4, "Errored"


running_statuses = (
    ImporterChunkStatus.WAITING,
    ImporterChunkStatus.RUNNING,
    ImporterChunkStatus.ERRORED,
)


class ImporterQuerySet(QuerySet):
    def has_dependencies(self) -> QuerySet:
        return self.filter(dependencies__chunks__status__in=running_statuses)

    def dependencies_finished(self) -> QuerySet:
        return self.exclude(dependencies__chunks__status__in=running_statuses)

    def depends_on(self, batch):
        return self.filter(batch_dependencies__depends_on=batch)

    def still_running(self):
        return self.filter(chunks__status__in=running_statuses)


class ImportBatchStatus(models.TextChoices):
    IMPORTING = "IMPORTING", "Importing"
    """The import process has not yet completed - possibly it is still queued,
    or envelope file parsing is ongoing, or something else."""
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    """The import process successfully completed with a correctly parsed
    envelope."""
    FAILED = "FAILED", "Failed"
    """The import process completed / terminated but finished in some error
    state."""
    FAILED_EMPTY = "FAILED_EMPTY", "Failed Empty"
    """The import was not able to complete, because there were no changes to
    import."""


class ImportBatch(TimestampedMixin):
    """
    A model to group chunks of TARIC XML data together.

    Usually the chunks are stored in direct sequence together however on
    occassion they are "split" by record code and chapter.

    Dependencies reflects other ImportBatch objects which this batch needs to
    finish before it can be imported.
    """

    name = models.CharField(max_length=100)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
    )
    goods_import = models.BooleanField(
        default=False,
    )
    """Indicates if this is intended to be a goods-only import and presented in
    the UI as such."""
    status = FSMField(
        default=ImportBatchStatus.IMPORTING,
        choices=ImportBatchStatus.choices,
        db_index=True,
        editable=False,
    )
    split_job = models.BooleanField(
        default=False,
    )
    dependencies = models.ManyToManyField(
        "self",
        through="BatchDependencies",
        symmetrical=False,
        blank=True,
    )
    """Relationship to other imports that must be completed before this import
    is processed."""
    workbasket = models.OneToOneField(
        "workbaskets.WorkBasket",
        on_delete=models.SET_NULL,
        null=True,
    )
    """The workbasket in which the parser creates its imported entities."""
    taric_file = models.FileField(
        storage=CommodityImporterStorage,
        default="",
        blank=True,
        validators=[validate_virus_check_result],
    )

    objects = models.Manager.from_queryset(ImporterQuerySet)()

    @transition(
        field=status,
        source=ImportBatchStatus.IMPORTING,
        target=ImportBatchStatus.SUCCEEDED,
        custom={"label": "Succeeded"},
    )
    def succeeded(self):
        """The import process completed and was successful."""
        logger.info(f"Transitioning status of import pk={self.pk} to SUCCEEDED.")

        if self.workbasket:
            if (
                not self.workbasket.tracked_models.exists()
                and self.workbasket.status == WorkflowStatus.EDITING
            ):
                # Successful imports with an empty workbasket are archived.
                logger.info(
                    f"Archiving empty workbasket pk={self.workbasket.pk} "
                    f"associated with SUCCEEDED import pk={self.pk}.",
                )
                self.workbasket.archive()
                self.workbasket.save()
        else:
            logger.info(
                f"No workbasket associated with import pk={self.pk}.",
            )

    @transition(
        field=status,
        source=ImportBatchStatus.IMPORTING,
        target=ImportBatchStatus.FAILED,
        custom={"label": "Failed"},
    )
    def failed(self):
        """The import process completed with an error condition."""
        logger.info(f"Transitioning status of import pk={self.pk} to FAILED.")
        if self.workbasket:
            if self.workbasket.tracked_models.exists():
                logger.info(
                    f"Clearing workbasket pk={self.workbasket.pk} contents "
                    f"associated with FAILED import pk={self.pk}.",
                )
                clear_workbasket(self.workbasket)

            if self.workbasket.status == WorkflowStatus.EDITING:
                logger.info(
                    f"Archiving workbasket pk={self.workbasket.pk} "
                    f"associated with FAILED import pk={self.pk}.",
                )
                self.workbasket.archive()
                self.workbasket.save()
        else:
            logger.info(
                f"FAILED import pk={self.pk}.",
            )

    def can_transition_to_failed_empty(self):
        """
        This check is used in the transition to failed empty, which should only
        be used before a workbasket is created.

        This is in support of the importerV2 which runs validation before
        committing anything to the database can can be used to indicate the
        import did not error but failed due to lack of content. The importerV1
        does not have this same behaviour, and will create a workbasket
        regardless, so use the failed transition in this case.
        """

        if self.workbasket:
            return False
        return True

    @transition(
        field=status,
        source=ImportBatchStatus.IMPORTING,
        target=ImportBatchStatus.FAILED_EMPTY,
        on_error=ImportBatchStatus.FAILED,
        conditions=[can_transition_to_failed_empty],
        custom={"label": "Failed Empty"},
    )
    def failed_empty(self):
        """The import process did not find any changes to import."""
        logger.info(f"Transitioning status of import pk={self.pk} to FAILED_EMPTY.")

        logger.info(
            f"FAILED_EMPTY import pk={self.pk}.",
        )

    @property
    def ready_chunks(self):
        """
        Return a QuerySet of chunks that have neither a status of DONE.

        or ERRORED - i.e. they have a status of WAITING or RUNNING.
        """
        return self.chunks.exclude(
            Q(status=ImporterChunkStatus.DONE) | Q(status=ImporterChunkStatus.ERRORED),
        ).defer("chunk_text")

    def __str__(self):
        return f"Batch pk:{self.pk}, name:{self.name}"

    def __repr__(self) -> str:
        return (
            f"ImportBatch(pk={self.pk}, name={self.name}, "
            f"author={self.author}, status={self.status})"
        )


class BatchImportError(TimestampedMixin):
    """
    Batch Import Error.

    This class is used to represent an error on import, and should be used to
    inform and assist to the import process when things go wrong.

    Most of the fields are populated with data read from the XML on import
    attempt, and are populated when a record cant be created or has issues.

    This class has a *-1 relationship with ImportBatch

    This object is used at the end of an import to iterate through found issues
    and persist them, there are other examples of issues being created outside
    the TARIC parsing process, a bad file for example but the main use is to
    persist detailed information for the user to review.
    """

    # the XML tag of an object, if required. Could be empty if an issue is related to a more generic error or the object type cant be determined
    object_type = models.CharField(max_length=250)

    # the XML tag of a related object, if required. Could be empty if an issue is related to a more generic error or the object
    # type cant be determined or there is no related object to the object type
    related_object_type = models.CharField(max_length=250)

    # A dictionary containing identity fields and values for an object related to the object being imported. This field will be populated typically if
    # an issue was identified where the related object expected by the import does not exist.
    related_object_identity_keys = models.JSONField(default=None, null=True)

    # Text description of the encountered issue
    description = models.CharField(max_length=2000)

    # Issue type, either ERROR, WARNING or INFO (from ImportIssueType choices)
    issue_type = models.CharField(
        max_length=50,
        choices=ImportIssueType.choices,
    )

    # The BatchImport the BatchImportError relates to
    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="issues",
    )

    # A dictionary of the values for the object where applicable. This field will be blank for generic errors not related to an object.
    object_data = models.JSONField(default=None, null=True)

    # Update type in the TARIC entry that the issue relates to, this can be null for issues relating to the import and not a specific
    # record but typically will be populated with the numeric value relating to the update type
    object_update_type: validators.UpdateType = models.PositiveSmallIntegerField(
        choices=validators.UpdateType.choices,
        db_index=True,
        blank=True,
        null=True,
    )

    # If this is related to a transaction, the transaction ID will be recorded here. This will be the ID in the XML.
    transaction_id = models.CharField(max_length=50, default=None)

    @property
    def object_update_type_name(self):
        if self.object_update_type:
            for update_type, update_type_name in validators.UpdateType.choices:
                if update_type == self.object_update_type:
                    return update_type_name
        return ""

    @property
    def object_data_to_str(self):
        str = ""
        if self.object_data:
            for key, value in self.object_data.items():
                str += f"{key}: {value}\n"

        return str

    @classmethod
    def create_from_import_issue_report_item(
        cls,
        issue: ImportIssueReportItem,
        import_batch: ImportBatch,
    ) -> None:
        """
        Creates a BatchImportError instance from the provided information,
        committed to the database.

        Args:
            issue: ImportIssueReportItem, An object containing information to report within BatchImportError
            import_batch: BatchImport, the batch object that the issue will be linked to

        Returns:
            None
        """
        cls.objects.create(
            batch=import_batch,
            object_type=issue.object_type,
            related_object_type=issue.related_object_type,
            related_object_identity_keys=issue.related_object_identity_keys,
            description=issue.description,
            issue_type=issue.issue_type,
            object_update_type=issue.object_update_type,
            object_data=issue.object_data,
            transaction_id=issue.transaction_id,
        )


class ImporterXMLChunk(TimestampedMixin):
    """A chunk of TARIC XML."""

    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="chunks",
    )
    record_code = models.CharField(max_length=3, null=True, blank=True, default=None)
    chapter = models.CharField(max_length=2, null=True, blank=True, default=None)

    chunk_number = models.PositiveSmallIntegerField()
    chunk_text = models.TextField(blank=False, null=False)

    status = models.PositiveSmallIntegerField(
        choices=ImporterChunkStatus.choices,
        default=1,
    )

    def __str__(self):
        name = "Chunk"
        if self.record_code:
            name += f" {self.record_code}"
        if self.chapter:
            name += f"-{self.chapter}"
        name += f" {self.chunk_number} - {self.get_status_display()} for {self.batch}"
        return name


class BatchDependencies(models.Model):
    dependent_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="batch_dependencies",
    )
    depends_on = models.ForeignKey(
        ImportBatch,
        on_delete=models.PROTECT,
        related_name="batch_dependents",
    )

    def __str__(self):
        return f"Batch {self.dependent_batch} depends on {self.depends_on}"
