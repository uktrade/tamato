from io import BytesIO
from unittest import mock

import pytest

from common.tests import factories
from importer import chunker


pytestmark = pytest.mark.django_db


def get_chunk_opener(id: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<env:envelope xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" '
        f'xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" id="{id:0>6}">'
    ).encode()


def get_basic_chunk_text(id: str) -> bytes:
    return get_chunk_opener(id) + b"</env:envelope>"


@mock.patch("importer.chunker.TemporaryFile")
def test_get_chunk(mock_temp_file: mock.MagicMock):
    mock_temp_file.side_effect = BytesIO
    chunks_in_progress = {}

    chunk1 = chunker.get_chunk(chunks_in_progress, "1")
    chunk2 = chunker.get_chunk(
        chunks_in_progress, "2", record_code="400", chapter_heading="01"
    )
    chunk1.seek(0)
    chunk2.seek(0)

    assert chunks_in_progress.get(None) == chunk1
    assert chunks_in_progress.get(("400", "01")) == chunk2
    assert chunk1.read() == get_chunk_opener("1")
    assert chunk2.read() == get_chunk_opener("2")


def test_close_chunk():
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
