from django.db import models


class ImporterChunkStatus(models.IntegerChoices):
    WAITING = 1, "WAITING"
    RUNNING = 2, "RUNNING"
    DONE = 3, "DONE"
    ERRORED = 4, "ERRORED"


class ImportBatch(models.Model):
    name = models.CharField(max_length=32)


class ImporterXMLChunk(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT)
    record_code = models.CharField(max_length=3, null=True, blank=True)
    chapter = models.CharField(max_length=2, null=True, blank=True)

    chunk_number = models.PositiveSmallIntegerField()
    chunk_text = models.TextField(blank=False, null=False)

    status = models.PositiveSmallIntegerField(
        choices=ImporterChunkStatus.choices, default=1
    )
