from unittest import mock

import pytest

from common.tests import factories
from importer import tasks
from importer.models import ImporterChunkStatus
from workbaskets.models import REVISION_ONLY

pytestmark = pytest.mark.django_db


@mock.patch("importer.tasks.find_and_run_next_batch_chunks")
def test_import_chunk(
    mock_find_and_run: mock.MagicMock,
    valid_user,
    chunk,
    object_nursery,
):
    tasks.import_chunk(
        chunk.pk,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )

    chunk.refresh_from_db()
    assert chunk.status == ImporterChunkStatus.DONE
    mock_find_and_run.assert_called_once_with(
        chunk.batch,
        "PUBLISHED",
        REVISION_ONLY,
        valid_user.username,
    )


@mock.patch("importer.tasks.process_taric_xml_stream", side_effect=KeyError("test"))
def test_import_chunk_failed(valid_user, chunk):
    try:
        tasks.import_chunk(
            chunk.pk,
            "PUBLISHED",
            "REVISION_ONLY",
            valid_user.username,
        )
    except KeyError:
        pass

    chunk.refresh_from_db()
    assert chunk.status == ImporterChunkStatus.ERRORED


@mock.patch("importer.tasks.import_chunk")
def test_setup_chunk_task_already_running(mock_import_chunk, batch, valid_user):
    """Assert that if a batch already has a running chunk, nothing happens."""
    factories.ImporterXMLChunkFactory.create(
        batch=batch,
        status=ImporterChunkStatus.RUNNING,
    )
    tasks.setup_chunk_task(
        batch,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )

    mock_import_chunk.delay.assert_not_called()


@mock.patch("importer.tasks.import_chunk")
def test_setup_chunk_task_no_chunks(mock_import_chunk, batch, valid_user):
    """Assert that if a batch has no chunks, nothing happens."""
    tasks.setup_chunk_task(
        batch,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )

    mock_import_chunk.delay.assert_not_called()


@mock.patch("importer.tasks.import_chunk")
def test_setup_chunk_task(mock_import_chunk, chunk, valid_user):
    """Assert that if a batch has no running chunks, a chunk is set to run."""
    tasks.setup_chunk_task(
        chunk.batch,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )

    chunk.refresh_from_db()

    assert chunk.status == ImporterChunkStatus.RUNNING
    mock_import_chunk.delay.assert_called_once_with(
        chunk.pk,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )


@mock.patch("importer.tasks.setup_chunk_task")
def test_find_and_run_next_batch_chunks_already_running(
    mock_setup_chunk_task,
    batch_dependency,
    valid_user,
):
    """Assert that if a batch already has running chunk, nothing happens."""
    batch_dependency.depends_on.chunks.update(status=ImporterChunkStatus.RUNNING)
    batch = batch_dependency.dependent_batch
    tasks.find_and_run_next_batch_chunks(
        batch,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )

    mock_setup_chunk_task.assert_not_called()
    assert list(batch.chunks.values_list("status", flat=True)) == [
        ImporterChunkStatus.WAITING,
    ]


@mock.patch("importer.tasks.import_chunk")
def test_find_and_run_next_batch_chunks_finished_runs_dependencies(
    mock_import_chunk,
    batch_dependency,
    valid_user,
):
    """Assert that if a batch has completely finished, it's dependencies start
    running."""
    batch_dependency.depends_on.chunks.update(status=ImporterChunkStatus.DONE)
    tasks.find_and_run_next_batch_chunks(
        batch_dependency.depends_on,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )
    batch = batch_dependency.dependent_batch

    assert list(batch.chunks.values_list("status", flat=True)) == [
        ImporterChunkStatus.RUNNING,
    ]
    mock_import_chunk.delay.assert_called_once_with(
        batch.chunks.first().pk,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )


@mock.patch("importer.tasks.import_chunk")
def test_find_and_run_next_batch_chunks(mock_import_chunk, batch, valid_user):
    """Assert that if a batch is not running that this starts the next chunk."""
    for chunk_number in range(1, 3):
        factories.ImporterXMLChunkFactory.create(batch=batch, chunk_number=chunk_number)

    tasks.find_and_run_next_batch_chunks(
        batch,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )

    assert batch.chunks.first().status == ImporterChunkStatus.RUNNING
    assert batch.chunks.last().status == ImporterChunkStatus.WAITING
    mock_import_chunk.delay.assert_called_once_with(
        batch.chunks.first().pk,
        "PUBLISHED",
        "REVISION_ONLY",
        valid_user.username,
    )
