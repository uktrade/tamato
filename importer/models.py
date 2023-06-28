from logging import getLogger

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models import QuerySet
from django_fsm import FSMField
from django_fsm import transition

from common.models import TimestampedMixin
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


class ImportBatch(TimestampedMixin):
    """
    A model to group chunks of TARIC XML data together.

    Usually the chunks are stored in direct sequence together however on
    occassion they are "split" by record code and chapter.

    Dependencies reflects other ImportBatch objects which this batch needs to
    finish before it can be imported.
    """

    name = models.CharField(max_length=32, unique=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
    )
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
    workbasket = models.OneToOneField(
        "workbaskets.WorkBasket",
        on_delete=models.SET_NULL,
        null=True,
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

    @transition(
        field=status,
        source=ImportBatchStatus.IMPORTING,
        target=ImportBatchStatus.FAILED,
        custom={"label": "Failed"},
    )
    def failed(self):
        """The import process completed with an error condition."""
        logger.info(f"Transitioning status of import pk={self.pk} to FAILED.")

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

    @property
    def ready_chunks(self):
        """Return a QuerySet of chunks that have neither a status of DONE
        or ERRORED - i.e. they have a status of WAITING or RUNNING."""
        return self.chunks.exclude(
            Q(status=ImporterChunkStatus.DONE) | Q(status=ImporterChunkStatus.ERRORED),
        ).defer("chunk_text")

    def __str__(self):
        return f"Batch {self.name}"


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
