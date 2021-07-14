import random
import time
from io import BytesIO
from logging import getLogger

from common.celery import app
from importer import models
from importer.taric import process_taric_xml_stream
from importer.utils import build_dependency_tree
from workbaskets.models import TransactionPartitionScheme

logger = getLogger(__name__)


@app.task
def import_chunk(
    chunk_pk: int,
    workbasket_status: str,
    partition_scheme: TransactionPartitionScheme,
    username: str,
):
    """
    Task for importing an XML chunk into the database.

    This task must ensure the chunks workbasket_status reflects the import
    process, whether it is currently running, errored or done. Once complete it
    is also responsible for finding and setting up the next chunk tasks.
    """
    chunk = models.ImporterXMLChunk.objects.get(pk=chunk_pk)

    logger.info(
        "RUNNING CHUNK Batch: %s Record code: %s Chapter heading: %s Chunk number: %d",
        chunk.batch.name,
        chunk.record_code,
        chunk.chapter,
        chunk.chunk_number,
    )

    chunk.status = models.ImporterChunkStatus.RUNNING
    chunk.save()

    try:
        process_taric_xml_stream(
            BytesIO(chunk.chunk_text.encode()),
            workbasket_status,
            partition_scheme,
            username,
        )
    except Exception as e:
        chunk.status = models.ImporterChunkStatus.ERRORED
        chunk.save()
        raise e

    chunk.status = models.ImporterChunkStatus.DONE
    chunk.save()

    find_and_run_next_batch_chunks(
        chunk.batch,
        workbasket_status,
        partition_scheme,
        username,
    )


def setup_chunk_task(
    batch: models.ImportBatch,
    workbasket_status: str,
    partition_scheme: TransactionPartitionScheme,
    username: str,
    record_code: str = None,
    **kwargs
):
    """
    Setup tasks to be run for the given chunk.

    Once a task is made it is important that the task is not duplicated. To stop
    this the system checks the chunk status. If the status is `RUNNING`,
    `ERRORED` or `DONE` the task is not setup. If the status is `WAITING` then
    the status is updated to `RUNNING` and the task is setup.
    """
    if batch.ready_chunks.filter(
        record_code=record_code, status=models.ImporterChunkStatus.RUNNING, **kwargs
    ).exists():
        return

    chunk = (
        batch.ready_chunks.filter(record_code=record_code, **kwargs)
        .order_by("chunk_number")
        .first()
    )

    if not chunk:
        return

    chunk.status = models.ImporterChunkStatus.RUNNING
    chunk.save()
    import_chunk.delay(
        chunk.pk,
        workbasket_status,
        partition_scheme,
        username,
    )


def find_and_run_next_batch_chunks(
    batch: models.ImportBatch,
    workbasket_status: str,
    partition_scheme: TransactionPartitionScheme,
    username: str,
):
    """
    Finds the next set of chunks for a batch to run.

    If the batch is not a split batch this is a simple process.

    If the batch is a split batch then this is more complicated.

    Split batches require the system to find all the current record codes
    that have run (or never existed) within a batch, build a dependency tree
    to then figure out which record codes therefore are now "unblocked" and can
    start running. Unblocked in this case meaning all the record codes the chunk
    may be dependent on have run.

    Record codes for split jobs are run in chunk order excluding two cases:

    1) Commodity codes can be split and run by chapter heading as well.
    2) Measures from split files are assumed to be able to run completely
       asynchronously and so all chunks are setup as tasks once unblocked.
    """
    if batch.dependencies.still_running().exists():
        return

    if not batch.ready_chunks.exists():  # The job is finished in this case.
        logger.info("finished")
        if (
            batch.chunks.exclude(status=models.ImporterChunkStatus.DONE)
            .defer("chunk_text")
            .exists()
        ):
            logger.info("Batch %s errored", batch)
            return
        for dependent_batch in models.ImportBatch.objects.depends_on(
            batch,
        ).dependencies_finished():
            logger.info("setting up tasks for %s", dependent_batch)
            find_and_run_next_batch_chunks(
                dependent_batch,
                workbasket_status,
                partition_scheme,
                username,
            )

    if not batch.split_job:  # We only run one chunk at a time when the job isn't split
        setup_chunk_task(batch, workbasket_status, partition_scheme, username)
        return

    # If the job is a split job (should only be used for seed files) the following logic applies.
    dependency_tree = build_dependency_tree()

    record_codes = set(
        batch.chunks.exclude(status=models.ImporterChunkStatus.DONE)
        .values_list("record_code", flat=True)
        .distinct(),
    )

    for key in list(dependency_tree.keys()):
        if key not in record_codes:
            dependency_tree.pop(key)

    unblocked_codes = [
        key
        for key, value in dependency_tree.items()
        if not value & dependency_tree.keys()
    ]

    logger.debug("records left %s", dependency_tree.keys())
    logger.debug("unblocked records %s", unblocked_codes)

    # HACK: reduce the possibility of early race conditions
    time.sleep(random.choice([x * 0.05 for x in range(0, 200)]))

    for code in unblocked_codes:
        # Special case: commodities can be split on chapter heading as well
        chunk_query = batch.ready_chunks.filter(record_code=code)
        if code == "400":
            for chapter in chunk_query.values_list("chapter", flat=True).distinct():
                setup_chunk_task(
                    batch,
                    workbasket_status,
                    partition_scheme,
                    username,
                    record_code=code,
                    chapter=chapter,
                )
        # Special case: measures when split can run entirely async
        elif code == "430":
            for chunk in chunk_query:
                setup_chunk_task(
                    batch,
                    workbasket_status,
                    partition_scheme,
                    username,
                    record_code=code,
                    chapter=chunk.chapter,
                    chunk_number=chunk.chunk_number,
                )
        else:
            setup_chunk_task(
                batch,
                workbasket_status,
                partition_scheme,
                username,
                record_code=code,
            )
