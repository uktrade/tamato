import xml.etree.ElementTree as ET
from io import BytesIO
from os import path
from typing import Sequence
from unittest import mock

import pytest
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict

from commodities.models.orm import GoodsNomenclature
from common.tests import factories
from common.tests.util import generate_test_import_xml
from importer import chunker
from importer.chunker import MAX_FILE_SIZE
from importer.chunker import chunk_taric
from importer.chunker import filter_transaction_records
from importer.chunker import get_chapter_heading
from importer.chunker import get_record_code
from importer.chunker import sort_comm_code_messages
from importer.chunker import sort_commodity_codes
from importer.chunker import write_transaction_to_chunk
from importer.models import ImporterXMLChunk
from importer.namespaces import TTags
from importer.namespaces import nsmap

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


@mock.patch("importer.chunker.TemporaryFile")
def test_get_chunk(mock_temp_file: mock.MagicMock):
    """Asserts that the correct chunk is found or created for writing to."""
    mock_temp_file.side_effect = BytesIO
    chunks_in_progress = {}

    chunk1 = chunker.get_chunk(chunks_in_progress, "1")
    chunk2 = chunker.get_chunk(
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


@mock.patch("importer.chunker.get_record_code")
def test_write_transaction_to_chunk_record_code_not_in_tree(
    get_record_code,
    envelope_commodity,
    taric_schema_tags,
    record_group,
):
    """Test that write_transaction_to_chunk returns None when record_code not
    found in dependency tree."""
    get_record_code.return_value = "rubbish"
    transaction = filter_snippet_transaction(
        envelope_commodity,
        taric_schema_tags,
        record_group,
    )
    transactions_in_progress = {}
    batch = factories.ImportBatchFactory.create(split_job=True)
    result = write_transaction_to_chunk(
        transaction,
        transactions_in_progress,
        batch,
        "1",
    )

    assert result is None


def test_get_record_code(envelope_commodity, taric_schema_tags, record_group):
    """Test that get_record_code returns the correct value for GoodsNomenclature
    when passed an xml ElementTree element."""
    transaction = filter_snippet_transaction(
        envelope_commodity,
        taric_schema_tags,
        record_group,
    )
    record_code = get_record_code(transaction)

    assert record_code == GoodsNomenclature.record_code


def test_get_chapter_heading_commodity(
    envelope_commodity,
    taric_schema_tags,
    record_group,
):
    """Test that get_chapter_heading accepts an xml ElementTree element and
    returns a string matching the goods nomenclature item_id in the xml."""
    transaction = filter_snippet_transaction(
        envelope_commodity,
        taric_schema_tags,
        record_group,
    )
    chapter_heading = get_chapter_heading(transaction)
    soup = BeautifulSoup(envelope_commodity)

    assert chapter_heading == soup.find("oub:goods.nomenclature.item.id").string[:2]


def test_get_chapter_heading_measure(envelope_measure, taric_schema_tags):
    """Test that get_chapter_heading accepts an xml ElementTree element and
    returns a string matching the measure's goods nomenclature item_id in the
    xml."""
    transaction = get_snippet_transaction(envelope_measure, taric_schema_tags)
    chapter_heading = get_chapter_heading(transaction)
    soup = BeautifulSoup(envelope_measure)

    assert chapter_heading == soup.find("oub:goods.nomenclature.item.id").string[:2]


@mock.patch("importer.chunker.get_chunk")
@mock.patch("importer.chunker.close_chunk")
def test_write_transaction_to_chunk_exceed_max_file_size(
    close_chunk,
    get_chunk,
    envelope_commodity,
    taric_schema_tags,
    record_group,
):
    """Tests that write_transaction_to_chunk calls close_chunk when get_chunk
    returns a chunk bigger than MAX_FILE_SIZE and that this chunk is popped from
    chunks_in_progress dict."""
    transaction = filter_snippet_transaction(
        envelope_commodity,
        taric_schema_tags,
        record_group,
    )
    chunks_in_progress = {}
    chunk = BytesIO()
    chunk.seek(MAX_FILE_SIZE + 1)
    record_code = get_record_code(transaction)
    chapter_heading = get_chapter_heading(transaction)
    key = (record_code, chapter_heading)

    def side_effect(in_progress, envelope_id, record_code=None, chapter_heading=None):
        chunks_in_progress[key] = chunk

        return chunk

    get_chunk.side_effect = side_effect
    batch = factories.ImportBatchFactory.create(split_job=True)
    write_transaction_to_chunk(transaction, chunks_in_progress, batch, "1")

    close_chunk.assert_called_with(chunk, batch, key)
    assert chunks_in_progress == {}


@pytest.mark.parametrize(
    "commodity_1_kwargs, commodity_2_kwargs",
    [
        ({"item_id": "0101000000"}, {"item_id": "0100000000"}),
        (
            {"item_id": "0100000000", "indent__indent": "01"},
            {"item_id": "0100000000", "indent__indent": "00"},
        ),
        (
            {"item_id": "0100000000", "indent__indent": "00", "suffix": "80"},
            {"item_id": "0100000000", "indent__indent": "00", "suffix": "70"},
        ),
        (
            {
                "item_id": "0100000000",
                "indent__indent": "00",
                "suffix": "80",
                "transaction_id": 2,
            },
            {
                "item_id": "0100000000",
                "indent__indent": "00",
                "suffix": "80",
                "transaction_id": 1,
            },
        ),
    ],
)
def test_sort_commodity_codes(
    taric_schema_tags,
    record_group,
    commodity_1_kwargs,
    commodity_2_kwargs,
):
    """Test that sort_commodity_codes sorts xml elements by item_id, indent,
    suffix, and transaction order."""
    transactions = []
    for comm_kwargs in [commodity_1_kwargs, commodity_2_kwargs]:
        transaction_id = comm_kwargs.pop("transaction_id", 0)
        comm = factories.GoodsNomenclatureFactory.create(**comm_kwargs)
        comm_data = model_to_dict(comm)
        comm_data.update(
            {
                "record_code": comm.record_code,
                "subrecord_code": comm.subrecord_code,
                "taric_template": "taric/goods_nomenclature.xml",
            },
        )
        indent = comm.indents.first()
        indent_data = model_to_dict(indent)
        indent_data.update(
            {
                "record_code": indent.record_code,
                "subrecord_code": indent.subrecord_code,
                "taric_template": "taric/goods_nomenclature_indent.xml",
            },
        )
        indent_data["indented_goods_nomenclature"] = {"item_id": comm.item_id}
        xml = generate_test_import_xml(
            [comm_data, indent_data],
            transaction_id=transaction_id,
        ).read()
        transaction = filter_snippet_transaction(xml, taric_schema_tags, record_group)
        transactions.append(transaction)

    sorted_transactions = sort_commodity_codes(transactions.copy())

    assert sorted_transactions[1] == transactions[0]
    assert sorted_transactions[0] == transactions[1]


def test_sort_comm_code_messages_returns_correctly(goods_xml_element_tree):
    """
    Test the behaviour of the sort_comm_code_messages sorting function.

    In this scenario the subrecord.code is 00 and there is no number.indents so
    the expected value is ('00', '00')
    """
    # get first transaction
    transaction = goods_xml_element_tree.find("*/env:app.message", nsmap)
    sorted_result = sort_comm_code_messages(transaction)
    assert sorted_result == ("00", "00")


def test_sort_comm_code_messages_returns_correctly_with_indents(
    goods_indents_xml_element_tree,
):
    """
    Test the behaviour of the sort_comm_code_messages sorting function.

    In this scenario the subrecord.code is 05 and the number.indents is 04
    """
    # get first transaction
    transaction = goods_indents_xml_element_tree.find("*/env:app.message", nsmap)
    sorted_result = sort_comm_code_messages(transaction)
    assert sorted_result == ("05", "04")
