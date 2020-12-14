import os
import xml.etree.cElementTree as etree
from collections import defaultdict
from pathlib import Path

from django.core.management import BaseCommand

from importer.namespaces import nsmap


MAX_FILE_SIZE = 1024 * 1024 * 100  # Will keep files roughly close to 100MB


def get_code_file(code, path, file_map, index=1) -> Path:
    try:
        filepath = file_map[code]
    except KeyError:
        filepath = path.joinpath(f"seed-{code}-{index}.xml")

        file_map[code] = filepath
        with open(filepath, "wb") as code_file:
            code_file.write(
                b"""\
<?xml version='1.0' encoding='UTF-8'?>
<env:envelope xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" xmlns:ns2="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" id="190003">
"""
            )

    return filepath


def close_file(filepath):
    with open(filepath, "ab") as code_file:
        code_file.write(
            b"""\
</env:envelope>"""
        )


def sort_commodity_codes(transactions):
    def comm_code_key(transaction):
        """
        Sort Commodity codes by item id and then transaction id.
        """
        item_ids = transaction.findall(
            "env:app.message/ns2:transmission/ns2:record/ns2:goods.nomenclature/ns2:goods.nomenclature.item.id",
            nsmap,
        )
        indents = transaction.findall(
            "env:app.message/ns2:transmission/ns2:record/ns2:goods.nomenclature.indents/ns2:number.indents",
            nsmap,
        )
        suffixes = transaction.findall(
            "env:app.message/ns2:transmission/ns2:record/ns2:goods.nomenclature/ns2:producline.suffix",
            nsmap,
        )
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
    code = message.find("ns2:transmission/ns2:record/ns2:subrecord.code", nsmap).text
    indent = message.find(
        "ns2:transmission/ns2:record/ns2:goods.nomenclature.indents/ns2:number.indents",
        nsmap,
    )
    indent = indent.text if indent is not None else "00"
    return code, indent


def rewrite_comm_codes(file_map, output_dir, record_code="400"):
    files = file_map[record_code]

    transactions = []

    for file in files:
        transactions.extend(etree.parse(file).getroot())

    transactions = sort_commodity_codes(transactions)

    files_in_progress = {}
    new_file_map = defaultdict(list)

    for transaction in transactions:
        transaction[:] = sorted(transaction, key=sort_comm_code_messages)
        write_transaction_to_file(
            transaction, record_code, output_dir, files_in_progress, new_file_map
        )

    return new_file_map, files_in_progress


def write_transaction_to_file(
    transaction, record_code, output_dir, files_in_progress, file_map
):
    if record_code in {"400", "430"}:
        item_ids = transaction.findall("*/*/*/*/ns2:goods.nomenclature.item.id", nsmap)
        record_code = "-".join(
            (record_code, item_ids[0].text[:2] if item_ids else "00")
        )
    filepath = get_code_file(
        record_code,
        output_dir,
        files_in_progress,
        len(file_map[record_code]),
    )

    with open(filepath, "ab") as code_file:
        code_file.write(
            etree.tostring(
                transaction
            )  # pythons XML doesn't write namespaces back correctly.
            .replace(b"<ns0:", b"<env:")
            .replace(b"<ns1:", b"<ns2:")
            .replace(b"</ns0:", b"</env:")
            .replace(b"</ns1:", b"</ns2:")
        )

    if os.path.getsize(filepath) > MAX_FILE_SIZE:
        close_file(filepath)
        file_map[record_code].append(files_in_progress.pop(record_code))


def split_taric(taric3_file, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    files_in_progress = {}
    file_map = defaultdict(list)
    xmlparser = etree.iterparse(taric3_file, ["end"])
    for event, elem in xmlparser:
        if not elem.tag == "{urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0}transaction":
            continue

        if int(elem.items()[0][1]) % 100000 == 0:
            print("transaction", int(elem.items()[0][1]))

        record_code = max(
            code.text
            for code in elem.findall(
                "env:app.message/ns2:transmission/ns2:record/ns2:record.code", nsmap
            )
        )

        write_transaction_to_file(
            elem, record_code, output_dir, files_in_progress, file_map
        )

        elem.clear()

    print("sorting comm codes")

    comm_file_map, comm_files_in_progress = rewrite_comm_codes(
        file_map,
        output_dir,
    )

    file_map.update(comm_file_map)
    files_in_progress.update(comm_files_in_progress)

    for record_code, filepath in files_in_progress.items():
        close_file(filepath)
        file_map[record_code].append(filepath)

    print(file_map)

    return file_map


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric3_file",
            help="The TARIC3 file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "-o",
            "--output-dir",
            help="Output directory for the split files",
            type=str,
            default="seed_files",
        )

    def handle(self, *args, **options):
        with open(options["taric3_file"], "rb") as taric3_file:
            split_taric(taric3_file=taric3_file, output_dir=options["output_dir"])
