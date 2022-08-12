import xml.etree.ElementTree as ET
from logging import getLogger
from tempfile import TemporaryFile
from typing import List
from typing import Optional
from typing import Sequence

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.loader import render_to_string

from importer import models
from importer.namespaces import make_schema_dataclass
from importer.namespaces import nsmap
from importer.namespaces import xsd_schema_paths
from importer.utils import dependency_tree

MAX_FILE_SIZE = 1024 * 1024 * 50  # Will keep chunks roughly close to 50MB
Tags = make_schema_dataclass(xsd_schema_paths)

logger = getLogger(__name__)


def get_chunk(
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


def sort_commodity_codes(transactions: List[ET.Element]) -> List[ET.Element]:
    """
    Sort the commodity code transactions by item ID, indent, suffix and
    transaction ID (which represents the order they were given in).

    Commodity codes in seed files have historically arrived unsorted. As the legacy system has
    no active representation of the commodity hierarchy (instead opting to use views) this works
    for the legacy system. However the new system has an in situ representation of the hierarchy.
    This representation requires the commodities to be entered in the right order to be built
    properly.

    The initial obvious way to sort things is via item ID (as 0100000000 would always come before
    0101000000 this way). However there are cases where multiple commodities have the same item ID.
    In this case they need to also be sorted on indent (as 00 would come before 01). Furthermore there
    are commodities with the same item ID and indent. In this case the commodities must also be sorted
    on suffix, as 80 means an endline product and therefore must come last always - all other suffixes
    are lesser than 80.

    Lastly if there is still a conflict commodities are ordered on transaction order.

    These four factors in that order produce an accurate hierarchical representation.
    """

    def comm_code_key(transaction):
        """Sort Commodity codes by item id, indent, suffix and transaction
        id."""
        item_ids = transaction.findall("*/*/*/*/ns2:goods.nomenclature.item.id", nsmap)
        indents = transaction.findall("*/*/*/*/ns2:number.indents", nsmap)
        suffixes = transaction.findall("*/*/*/*/ns2:producline.suffix", nsmap)

        # Find the item ID, indent and suffix. If one of these isn't found then it is
        # replaced with the largest possible number of equivalent size so that it is
        # sorted to the end.
        item_id = min(item.text for item in item_ids) if item_ids else "999999999999"
        indent = min(indent_obj.text for indent_obj in indents) if indents else "99"

        suffix = (
            min("00" if suffix.text != "80" else "80" for suffix in suffixes)
            if suffixes
            else "99"
        )

        return item_id, indent, suffix, transaction.items()[0][1]

    transactions.sort(key=comm_code_key)
    return transactions


def sort_comm_code_messages(message):
    """
    Sort the messages within a commodity code transaction.

    On top of commodity code transactions being unsorted at times the messages
    within the transaction are also out of order. This can mean indents are
    given before the codes they are indenting and other similar issues. In this
    case the messages only need to be sorted by subrecord code and indent to
    produce the correct order.
    """
    code = message.find("*/*/ns2:subrecord.code", nsmap).text
    indent = message.find("*/*/*/ns2:number.indents", nsmap)

    # If no indent found then sort the message to the front by giving the indent "00"
    # This guarantees objects not related to indents get done first (as nothing has
    # a relationship to indents).
    indent = indent.text if indent is not None else "00"
    return code, indent


def rewrite_comm_codes(batch: models.ImportBatch, envelope_id: str, record_code="400"):
    """
    Take the given commodity code data and rewrite it in the correct order
    required by the hierarchical tree.

    Commodity codes in seed files often are given out of order which breaks the hierarchical
    tree representing them. This function takes all transactions with the relevant record_code
    (400), sorts them and rewrites them in the expected order.

    N.B. This happens entirely within memory.
    """
    chunks = batch.chunks.filter(record_code=record_code)

    transactions = []

    for chunk in chunks:
        transactions.extend(ET.fromstring(chunk.chunk_text))

    logger.info("%d to sort, deleting old ones", len(transactions))

    chunks.delete()

    transactions = sort_commodity_codes(transactions)

    chunks_in_progress = {}

    for transaction in transactions:
        transaction[:] = sorted(transaction, key=sort_comm_code_messages)
        write_transaction_to_chunk(transaction, chunks_in_progress, batch, envelope_id)

    for key, chunk in chunks_in_progress.items():
        close_chunk(chunk, batch, key)


def get_record_code(transaction: ET.Element) -> str:
    return max(
        code.text for code in transaction.findall("*/*/*/ns2:record.code", nsmap)
    )


def get_chapter_heading(transaction: ET.Element) -> str:
    item_id = transaction.find(
        "*/*/*/*/ns2:goods.nomenclature.item.id",
        nsmap,
    )
    chapter_heading = item_id.text[:2] if item_id else "00"

    return chapter_heading


def write_transaction_to_chunk(
    transaction: ET.Element,
    chunks_in_progress: dict,
    batch: models.ImportBatch,
    envelope_id: str,
):
    """
    Write a given transaction to the relevant chunk.

    Finds the chunk to write to. If the batch is a split_job the chunk is based on record code
    and possibly chapter heading (for commodities and measures). If the batch is not a split
    job it simply uses the current or next chunk.

    If a chunk reaches the given size limit it is written to the database and a new chunk
    started.
    """
    chapter_heading = None

    if batch.split_job:
        record_code = get_record_code(transaction)

        if record_code not in dependency_tree:
            return

        # Commodities and measures are special cases which can be split on chapter heading as well.
        if record_code in {"400", "430"}:
            chapter_heading = get_chapter_heading(transaction)

    else:
        record_code = None

    chunk = get_chunk(
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

    if chunk.tell() > MAX_FILE_SIZE:
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

    Record identifiers are concatenated record_code and subrecord_code child element values.

    Returns the a copy of the transaction element with non-matching records removed.
    Returns the untouched transaction if record_group is none.
    Returns None if there are no matching records in the transaction.
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
) -> models.ImportBatch:
    """
    Parses a TARIC3 XML stream and breaks it into a batch of chunks.

    All chunks are written to the database. If the batch is intended to be split
    on record code then the commodity codes are also sorted into the correct
    order.
    """
    chunks_in_progress = {}
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

    for key, chunk in chunks_in_progress.items():
        close_chunk(chunk, batch, key)

    if batch.split_job:
        rewrite_comm_codes(batch, envelope_id)

    return batch
