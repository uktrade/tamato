from logging import getLogger
from typing import Sequence

from django.contrib.auth.models import User

import taric_parsers.importer
from common.celery import app
from importer.models import BatchImportError
from importer.models import ImportBatch
from importer.models import ImporterChunkStatus
from importer.models import ImporterXMLChunk
from importer.models import ImportIssueType
from taric_parsers.taric_xml_source import TaricXMLStringSource
from workbaskets.models import WorkBasket
from workbaskets.models import get_partition_scheme

logger = getLogger(__name__)


@app.task
def parse_and_import(
    chunk_pk: int,
    username: str,
    workbasket_title: str,
):
    """
    Task for importing an XML chunk into the database.

    This task must ensure the chunks workbasket_status reflects the import
    process, whether it is currently running, errored or done. Once complete it
    is also responsible for finding and setting up the next chunk tasks.
    """

    chunk = ImporterXMLChunk.objects.get(pk=chunk_pk)
    batch = chunk.batch

    logger.info(
        "RUNNING CHUNK Batch: %s Record code: %s Chapter heading: %s Chunk number: %d",
        batch.name,
        chunk.record_code,
        chunk.chapter,
        chunk.chunk_number,
    )

    chunk.status = ImporterChunkStatus.RUNNING
    chunk.save()

    try:
        importer = taric_parsers.importer.TaricImporter(
            import_batch=batch,
            taric_xml_source=TaricXMLStringSource(chunk.chunk_text),
        )

        if importer.can_save():
            # at this point we can create the workbasket and have a high degree of confidence that the import will complete.
            import_user = User.objects.all().get(username=username, is_active=True)
            workbasket = WorkBasket.objects.create(
                title=workbasket_title,
                author=import_user,
            )

            # need to associate workbasket with the ImportBatch
            batch.workbasket = workbasket
            batch.save()

            importer.process_and_save_if_valid(workbasket)
        elif importer.is_empty():
            importer.clear_issues()
        else:
            importer.commit_issues()

        if len(importer.issues(filter_by_issue_type=ImportIssueType.ERROR)) > 0:
            chunk.status = ImporterChunkStatus.ERRORED
        else:
            chunk.status = ImporterChunkStatus.DONE

        chunk.save()

    except Exception as e:
        batch.failed()
        batch.save()

        chunk.status = ImporterChunkStatus.ERRORED
        chunk.save()

        import_error = BatchImportError(
            object_type="Exception at Chunk Creation",
            related_object_type="",
            related_object_identity_keys="",
            description=str(e),
            batch=batch,
            object_update_type=None,
            object_data=None,
            transaction_id=0,
            issue_type=ImportIssueType.ERROR,
        )

        import_error.save()

        raise e

    batch_errored_chunks = batch.chunks.filter(
        status=ImporterChunkStatus.ERRORED,
    )

    if not batch.ready_chunks.exists():
        if not batch_errored_chunks:
            if len(batch.chunks) == 0:
                # This indicates that there was not any data to import. The batch should.
                # be flagged with status FAILED_EMPTY.
                batch.failed_empty()
            else:
                # This was batch's last chunk requiring processing, and it has no
                # chunks with status ERRORED, so transition batch to SUCCEEDED.
                batch.succeeded()
        else:
            # This was batch's last chunk requiring processing, and it did have
            # chunks with status ERRORED, so transition batch to ERRORED.
            batch.failed()
        batch.save()


def setup_new_chunk_task(
    batch: ImportBatch,
    workbasket_id: str,
    workbasket_status: str,
    partition_scheme_setting: str,
    username: str,
    record_code: str = None,
    record_group: Sequence[str] = None,
    **kwargs,
):
    """
    Setup new task to be run for the given chunk.

    Once a task is made it is important that the task is not duplicated. To stop
    this the system checks the chunk status. If the status is `RUNNING`,
    `ERRORED` or `DONE` the task is not setup. If the status is `WAITING` then
    the status is updated to `RUNNING` and the task is set up.
    """

    # Call get_partition_scheme before invoking celery so that it can raise ImproperlyConfigured if
    # partition_scheme_setting is invalid.

    get_partition_scheme(partition_scheme_setting)

    if batch.ready_chunks.filter(
        record_code=record_code,
        status=ImporterChunkStatus.RUNNING,
        **kwargs,
    ).exists():
        return

    chunk = (
        batch.ready_chunks.filter(record_code=record_code, **kwargs)
        .order_by("chunk_number")
        .first()
    )

    if not chunk:
        return

    chunk.status = ImporterChunkStatus.RUNNING
    chunk.save()
    parse_and_import.delay(
        chunk.pk,
        workbasket_id,
        workbasket_status,
        partition_scheme_setting,
        username,
        record_group=record_group,
    )
