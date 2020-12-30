from django.db import models
from django.db.models import Q

from common.models import TimestampedMixin


class ImporterChunkStatus(models.IntegerChoices):
    WAITING = 1, "WAITING"
    RUNNING = 2, "RUNNING"
    DONE = 3, "DONE"
    ERRORED = 4, "ERRORED"


class ImportBatch(TimestampedMixin):
    name = models.CharField(max_length=32, unique=True)
    split_job = models.BooleanField(
        default=False
    )  # XXX could be termed "seed file" instead?

    @property
    def ready_chunks(self):
        return self.chunks.exclude(
            Q(status=ImporterChunkStatus.DONE) | Q(status=ImporterChunkStatus.ERRORED)
        ).defer("chunk_text")

    def __str__(self):
        return f"Batch {self.name}"


class ImporterXMLChunk(TimestampedMixin):
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.PROTECT, related_name="chunks"
    )
    record_code = models.CharField(max_length=3, null=True, blank=True, default=None)
    chapter = models.CharField(max_length=2, null=True, blank=True, default=None)

    chunk_number = models.PositiveSmallIntegerField()
    chunk_text = models.TextField(blank=False, null=False)

    status = models.PositiveSmallIntegerField(
        choices=ImporterChunkStatus.choices, default=1
    )

    def __str__(self):
        name = "Chunk"
        if self.record_code:
            name += f" {self.record_code}"
        if self.chapter:
            name += f"-{self.chapter}"
        name += f" {self.chunk_number} - {self.get_status_display()} for {self.batch}"
        return name
