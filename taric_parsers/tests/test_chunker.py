import xml.etree.ElementTree as ET
from io import BytesIO
from os import path
from typing import Sequence
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from common.tests import factories
from importer.models import ImporterXMLChunk
from taric_parsers import chunker
from taric_parsers.chunker import chunk_taric
from taric_parsers.chunker import filter_transaction_records
from taric_parsers.chunker import find_or_create_chunk
from taric_parsers.namespaces import TTags

from .test_namespaces import get_snippet_transaction

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")

pytestmark = pytest.mark.django_db


def get_chunk_opener(id: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<env:envelope xmlns="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" '
        f'xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" id="{id:0>6}">'
    ).encode()


def get_basic_chunk_text(id: str) -> bytes:
    return get_chunk_opener(id) + b"</env:envelope>"


def filter_snippet_transaction(
    xml: str,
    Tags: TTags,
    record_group: Sequence[str],
) -> ET.Element:
    """Returns a filtered transaction with matching records from a record_group
    only."""
    transaction = get_snippet_transaction(xml, Tags)
    return filter_transaction_records(transaction, record_group)


@pytest.mark.new_importer
@mock.patch("taric_parsers.chunker.TemporaryFile")
def test_get_chunk(mock_temp_file: mock.MagicMock):
    """Asserts that the correct chunk is found or created for writing to."""
    mock_temp_file.side_effect = BytesIO
    chunks_in_progress = {}

    chunk1 = find_or_create_chunk(chunks_in_progress, "1")
    chunk2 = find_or_create_chunk(
        chunks_in_progress,
        "2",
        record_code="400",
        chapter_heading="01",
    )
    chunk1.seek(0)
    chunk2.seek(0)

    assert chunks_in_progress.get(None) == chunk1
    assert chunks_in_progress.get(("400", "01")) == chunk2
    assert chunk1.read() == get_chunk_opener("1")
    assert chunk2.read() == get_chunk_opener("2")


@pytest.mark.new_importer
def test_close_chunk():
    """Asserts that chunks are properly closed and added to the batch."""
    batch = factories.ImportBatchFactory.create()
    chunk1 = BytesIO()
    chunk2 = BytesIO()
    chunk1.write(get_chunk_opener("1"))
    chunk2.write(get_chunk_opener("2"))

    assert batch.chunks.count() == 0

    chunker.close_chunk(chunk1, batch, None)
    chunker.close_chunk(chunk2, batch, ("400", "01"))

    assert batch.chunks.count() == 2
    assert (
        batch.chunks.get(record_code=None).chunk_text
        == get_basic_chunk_text("1").decode()
    )
    assert (
        batch.chunks.get(record_code=400, chapter="01").chunk_text
        == get_basic_chunk_text("2").decode()
    )


@pytest.mark.new_importer
def test_filter_transaction_records_positive(
    taric_schema_tags,
    record_group,
    envelope_commodity,
):
    """Asserts that matching records from the record_group are preserved in the
    transaction."""

    # filter_snippet_transaction calls get_snippet_transaction,
    # which gets the first transaction from an xml envelope,
    # and then calls filter_transaction_records, which checks whether this transaction contains
    # a record identifier matching a value in TARIC_RECORD_CODES["commodities"]
    transaction = filter_snippet_transaction(
        envelope_commodity,
        taric_schema_tags,
        record_group,
    )

    assert transaction is not None
    assert len(transaction) == 1


@pytest.mark.new_importer
def test_filter_transaction_records_negative(
    taric_schema_tags,
    record_group,
    envelope_measure,
):
    """Asserts that non-matching records from the record_group are removed from
    the transaction."""
    transaction = filter_snippet_transaction(
        envelope_measure,
        taric_schema_tags,
        record_group,
    )

    assert transaction is None


@pytest.mark.new_importer
def test_chunk_taric(example_goods_taric_file_location):
    """Tests that the chunker creates an ImporterXMLChunk object in the db from
    the loaded XML file."""
    assert not ImporterXMLChunk.objects.count()
    with open(f"{example_goods_taric_file_location}", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("goods.xml", content, content_type="text/xml")
    batch = factories.ImportBatchFactory.create()
    chunk_taric(taric_file, batch)
    assert ImporterXMLChunk.objects.count()
    chunk = ImporterXMLChunk.objects.first()
    assert chunk.chunk_text


@pytest.mark.new_importer
def test_chunk_taric_fails_with_split_job(example_goods_taric_file_location):
    """Tests that the chunker creates an ImporterXMLChunk object in the db from
    the loaded XML file."""
    assert not ImporterXMLChunk.objects.count()
    with open(f"{example_goods_taric_file_location}", "rb") as f:
        content = f.read()
    taric_file = SimpleUploadedFile("goods.xml", content, content_type="text/xml")
    batch = factories.ImportBatchFactory.create(split_job=True)
    with pytest.raises(Exception) as e:
        chunk_taric(taric_file, batch)

    assert (
        "Unexpected split job, split jobs are not compatible with importer v2. "
        in str(e)
    )
    assert "Please split files up before importing." in str(e)
