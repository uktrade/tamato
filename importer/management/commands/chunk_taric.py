import xml.etree.cElementTree as etree
from logging import getLogger
from tempfile import TemporaryFile

from django.core.management import BaseCommand
from django.template.loader import render_to_string

from importer import models
from importer.namespaces import nsmap
from importer.utils import dependency_tree

MAX_FILE_SIZE = 1024 * 1024 * 50  # Will keep chunks roughly close to 50MB

ENVELOPE_TAG = "{urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0}envelope"
TRANSACTION_TAG = "{urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0}transaction"

logger = getLogger(__name__)


def get_chunk(
    chunks_in_progress: dict,
    batch: models.ImportBatch,
    record_code=None,
    chapter_heading=None,
) -> TemporaryFile:
    """
    Find or create the chunk currently being written to. If the chunk has to be created
    write the initial envelope header for it.

    Chunks are eventually written to the database as Django models, however handling the
    large strings and storing it in memory before updating is (I believe) O(n!). Whereas
    storing tempfiles and simply appending to the files before writing to the database is
    O(n).
    """
    key = (record_code, chapter_heading) if chapter_heading else record_code

    try:
        chunk = chunks_in_progress[key]
    except KeyError:
        chunk = TemporaryFile()
        chunk.write(
            render_to_string(template_name="common/taric/start_file.xml").encode()
        )
        chunk.write(
            render_to_string(
                template_name="common/taric/start_envelope.xml",
                context={"envelope_id": batch.name},
            ).encode()
        )
        chunks_in_progress[key] = chunk

    return chunk


def close_chunk(chunk: TemporaryFile, batch: models.ImportBatch, key):
    """
    Write a chunk to the database.

    To close a chunk properly it must have the envelope closing tag added
    before being read into the db.
    """
    chunk.write(
        render_to_string(template_name="common/taric/end_envelope.xml").encode()
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
            record_code=record_code, chapter=chapter_heading
        ).count(),
        chunk_text=chunk.read().decode(),
    )
    chunk.close()

    logger.info(
        "closed chunk with code %s and chapter %s", record_code, chapter_heading
    )


def sort_commodity_codes(transactions):
    """
    Sort the commodity code transactions by item ID, indent, suffix and transaction ID (which
    represents the order they were given in).

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

    These for factors in that order produce an accurate hierarchical representation.
    """

    def comm_code_key(transaction):
        """
        Sort Commodity codes by item id, indent, suffix and transaction id.
        """
        item_ids = transaction.findall("*/*/*/*/ns2:goods.nomenclature.item.id", nsmap)
        indents = transaction.findall("*/*/*/*/ns2:number.indents", nsmap)
        suffixes = transaction.findall("*/*/*/*/ns2:producline.suffix", nsmap)

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

    On top of commodity code transactions being unsorted at times the messages within
    the transaction are also out of order. This can mean indents are given before the codes they
    are indenting and other similar issues. In this case the messages only need to be sorted by
    subrecord code and indent to produce the correct order.
    """
    code = message.find("*/*/ns2:subrecord.code", nsmap).text
    indent = message.find("*/*/*/ns2:number.indents", nsmap)
    indent = indent.text if indent is not None else "00"
    return code, indent


def rewrite_comm_codes(batch: models.ImportBatch, record_code="400"):
    """
    Take the given commodity code data and rewrite it in the correct order required by the
    hierarchical tree.

    Commodity codes in seed files often are given out of order which breaks the hierarchical
    tree representing them. This function takes all transactions with the relevant record_code
    (400), sorts them and rewrites them in the expected order.

    N.B. This happens entirely within memory.
    """
    chunks = batch.chunks.filter(record_code=record_code)

    transactions = []

    for chunk in chunks:
        transactions.extend(etree.fromstring(chunk.chunk_text))

    logger.info("%d to sort, deleting old ones", len(transactions))

    chunks.delete()

    transactions = sort_commodity_codes(transactions)

    chunks_in_progress = {}

    for transaction in transactions:
        transaction[:] = sorted(transaction, key=sort_comm_code_messages)
        write_transaction_to_chunk(transaction, chunks_in_progress, batch)

    for key, chunk in chunks_in_progress.items():
        close_chunk(chunk, batch, key)


def write_transaction_to_chunk(
    transaction: etree.Element,
    chunks_in_progress: dict,
    batch: models.ImportBatch,
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
        record_code = max(
            code.text for code in transaction.findall("*/*/*/ns2:record.code", nsmap)
        )

        if record_code not in dependency_tree:
            return

        # Commodities and measures are special cases which can be split on chapter heading as well.
        if record_code in {"400", "430"}:
            item_ids = transaction.findall(
                "*/*/*/*/ns2:goods.nomenclature.item.id", nsmap
            )
            chapter_heading = item_ids[0].text[:2] if item_ids else "00"

    else:
        record_code = None

    chunk = get_chunk(
        chunks_in_progress,
        batch,
        record_code=record_code,
        chapter_heading=chapter_heading,
    )

    chunk.write(
        etree.tostring(
            transaction
        )  # pythons XML doesn't write namespaces back correctly.
        .replace(b"<ns0:", b"<env:")
        .replace(b"<ns1:", b"<ns2:")
        .replace(b"</ns0:", b"</env:")
        .replace(b"</ns1:", b"</ns2:")
        .replace(b"xmlns:ns0=", b"xmlns:env=")
        .replace(b"xmlns:ns1=", b"xmlns:ns2=")
    )

    if chunk.tell() > MAX_FILE_SIZE:
        key = (record_code, chapter_heading) if chapter_heading else record_code
        close_chunk(chunk, batch, key)
        chunks_in_progress.pop(key)


def chunk_taric(
    taric3_file, split_on_code: bool = False, dependencies=None
) -> models.ImportBatch:
    """
    Parses a TARIC3 XML stream and breaks it into a batch of chunks. All chunks are written to
    the database. If the batch is intended to be split on record code then the commodity codes
    are also sorted into the correct order.
    """
    chunks_in_progress = {}
    xmlparser = etree.iterparse(taric3_file, ["start", "end"])

    batch = None
    while batch is None:
        event, elem = next(xmlparser)
        if event == "start" and elem.tag == ENVELOPE_TAG:
            batch = models.ImportBatch.objects.create(
                name=elem.get("id", taric3_file.name), split_job=split_on_code
            )

    for dependency in dependencies or []:
        models.BatchDependencies.objects.create(
            depends_on=models.ImportBatch.objects.get(name=dependency),
            dependent_batch=batch,
        )

    element_counter = 0
    for event, elem in xmlparser:
        if event != "end" or elem.tag != TRANSACTION_TAG:
            continue

        write_transaction_to_chunk(elem, chunks_in_progress, batch)
        elem.clear()

        element_counter += 1
        if element_counter % 100000 == 0:
            logger.info("%d transactions done", element_counter)

    for key, chunk in chunks_in_progress.items():
        close_chunk(chunk, batch, key)

    if split_on_code:
        rewrite_comm_codes(batch)

    return batch


class Command(BaseCommand):
    help = "Chunk data from a TARIC XML file into chunks for import"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric3_file",
            help="The TARIC3 file to be parsed.",
            type=str,
        )

        parser.add_argument(
            "-s",
            "--split-codes",
            help="Split the file based on record codes",
            action="store_true",
        )
        parser.add_argument(
            "-d",
            "--dependencies",
            help="List of batches that need to finish before the current batch can run",
            action="append",
        )

    def handle(self, *args, **options):
        with open(options["taric3_file"], "rb") as taric3_file:
            chunk_taric(
                taric3_file=taric3_file,
                split_on_code=options["split_codes"],
                dependencies=options["dependencies"],
            )
