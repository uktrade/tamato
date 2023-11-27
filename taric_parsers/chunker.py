import os
import xml.etree.ElementTree as ET
from logging import getLogger
from tempfile import TemporaryFile
from typing import Optional
from typing import Sequence

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.loader import render_to_string

from importer import models
from importer.models import BatchImportError
from importer.models import ImportIssueType
from settings import MAX_IMPORT_FILE_SIZE
from taric_parsers.namespaces import make_schema_dataclass
from taric_parsers.namespaces import xsd_schema_paths

Tags = make_schema_dataclass(xsd_schema_paths)

logger = getLogger(__name__)


def find_or_create_chunk(
    chunks_in_progress: dict,
    envelope_id: str,
    record_code=None,
    chapter_heading=None,
) -> TemporaryFile:
    """
    Find or create the chunk currently being written to. If the chunk has to be
    created write the initial envelope header for it.

    Chunks are eventually written to the database as Django models, however
    handling the large strings and storing it in memory before updating is (I
    believe) O(n!). Whereas storing tempfiles and simply appending to the files
    before writing to the database is O(n).
    """
    key = (record_code, chapter_heading) if chapter_heading else record_code

    try:
        chunk = chunks_in_progress[key]
    except KeyError:
        chunk = TemporaryFile()
        chunk.write(
            render_to_string(template_name="common/taric/start_file.xml").encode(),
        )
        chunk.write(
            render_to_string(
                template_name="common/taric/start_envelope.xml",
                context={"envelope_id": envelope_id},
            ).encode(),
        )
        chunks_in_progress[key] = chunk

    return chunk


def close_chunk(chunk: TemporaryFile, batch: models.ImportBatch, key):
    """
    Write a chunk to the database.

    To close a chunk properly it must have the envelope closing tag added before
    being read into the db.
    """
    chunk.write(
        render_to_string(template_name="common/taric/end_envelope.xml").encode(),
    )
    chunk.seek(0)
    if isinstance(key, tuple):
        record_code, chapter_heading = key
    else:
        record_code = key
        chapter_heading = None

    models.ImporterXMLChunk.objects.create(
        batch=batch,
        record_code=record_code,
        chapter=chapter_heading,
        chunk_number=batch.chunks.filter(
            record_code=record_code,
            chapter=chapter_heading,
        ).count(),
        chunk_text=chunk.read().decode(),
    )
    chunk.close()

    logger.info(
        "closed chunk with code %s and chapter %s",
        record_code,
        chapter_heading,
    )


def write_transaction_to_chunk(
    transaction: ET.Element,
    chunks_in_progress: dict,
    batch: models.ImportBatch,
    envelope_id: str,
):
    """
    Write a given transaction to the relevant chunk.

    Finds the chunk to write to. If the batch is a split_job the chunk is based
    on record code and possibly chapter heading (for commodities and measures).
    If the batch is not a split job it simply uses the current or next chunk.

    If a chunk reaches the given size limit it is written to the database and a
    new chunk started.
    """
    chapter_heading = None
    record_code = None

    chunk = find_or_create_chunk(
        chunks_in_progress,
        envelope_id,
        record_code=record_code,
        chapter_heading=chapter_heading,
    )

    chunk.write(
        ET.tostring(
            transaction,
        )  # pythons XML doesn't write namespaces back correctly.
        .replace(b"<ns0:", b"<env:")
        .replace(b"<ns1:", b"<ns2:")
        .replace(b"</ns0:", b"</env:")
        .replace(b"</ns1:", b"</ns2:")
        .replace(b"xmlns:ns0=", b"xmlns:env=")
        .replace(b"xmlns:ns1=", b"xmlns:ns2="),
    )

    if chunk.tell() > MAX_IMPORT_FILE_SIZE:
        key = (record_code, chapter_heading) if chapter_heading else record_code
        close_chunk(chunk, batch, key)
        chunks_in_progress.pop(key)


def filter_transaction_records(
    elem: ET.Element,
    record_group: Sequence[str],
) -> Optional[ET.Element]:
    """
    Filters the records in a transaction based on record codes in the record
    group.

    Record identifiers are concatenated record_code and subrecord_code child
    element values.

    Returns the a copy of the transaction element with non-matching records
    removed. Returns the untouched transaction if record_group is none. Returns
    None if there are no matching records in the transaction.
    """
    if record_group is None:
        return elem

    transaction_id = elem.get("id")

    n = len(elem)

    pending_removals = []

    for message in Tags.ENV_APP_MESSAGE.iter(elem):
        for transmission in Tags.OUB_TRANSMISSION.iter(message):
            for record in Tags.OUB_RECORD.iter(transmission):
                record_code = Tags.OUB_RECORD_CODE.first(record).text
                subrecord_code = Tags.OUB_SUBRECORD_CODE.first(record).text
                identifier = f"{record_code}{subrecord_code}"

                if identifier not in record_group:
                    pending_removals.append((message, transmission, record, identifier))

    for message, transmission, record, identifier in pending_removals:
        sequence_number = Tags.OUB_RECORD_SEQUENCE_NUMBER.first(record).text

        transmission.remove(record)

        msg = "Transaction %s: Removed record with code %s and sequence number %s."
        logger.info(msg, transaction_id, identifier, sequence_number)

        if not transmission:
            message.remove(transmission)

        if not message:
            elem.remove(message)

    if elem:
        msg = "Transaction %s: %d out of %d records match the record group."
        logger.info(msg, transaction_id, len(elem), n)
        return elem

    msg = "Transaction id %s: Removed - no matching records. "
    logger.info(msg, transaction_id)
    return


def chunk_taric(
    taric3_file: InMemoryUploadedFile,
    batch: models.ImportBatch,
    record_group: Sequence[str] = None,
) -> int:
    """
    Parses a TARIC3 XML stream and breaks it into a batch of chunks.

    All chunks are written to the database. If the batch is intended to be split
    on record code then the commodity codes are also sorted into the correct
    order.

    Returns the number of chunks created and associated with `batch`.
    """
    chunks_in_progress = {}

    # set file position to start of stream
    taric3_file.seek(0, os.SEEK_SET)
    xmlparser = ET.iterparse(taric3_file, ["start", "end"])

    element_counter = 0
    envelope_id = None
    for event, elem in xmlparser:
        if event == "start" and elem.tag == Tags.ENV_ENVELOPE.qualified_name:
            envelope_id = elem.get("id", taric3_file.name)
        if event != "end" or elem.tag != Tags.ENV_TRANSACTION.qualified_name:
            continue

        transaction = filter_transaction_records(elem, record_group)

        if transaction is None:
            continue

        write_transaction_to_chunk(transaction, chunks_in_progress, batch, envelope_id)
        transaction.clear()

        element_counter += 1
        if element_counter % 100000 == 0:
            logger.info("%d transactions done", element_counter)

    chunk_count = len(chunks_in_progress)

    for key, chunk in chunks_in_progress.items():
        close_chunk(chunk, batch, key)

    if batch.split_job:
        BatchImportError.objects.create(
            batch=batch,
            description="This Import has been flagged as a split job. Please review file size. Maximum import size is 50mb, "
            "anything larger than this should be split before attempting import. This importer does not support "
            "split jobs",
            object_update_type=None,
            issue_type=ImportIssueType.ERROR,
            transaction_id="",
            object_details="",
            related_object_identity_keys="",
            object_type="",
        )
        raise Exception(
            "Unexpected split job, split jobs are not compatible with importer v2. Please split files up before importing.",
        )

    return chunk_count
