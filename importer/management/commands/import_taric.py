import xml.etree.ElementTree as etree

from django.core.management import BaseCommand

from importer.namespaces import nsmap
from importer.taric import Envelope
from workbaskets.validators import WorkflowStatus


XML_CHUNK_SIZE = 4096


def import_taric(taric3_file, username, status):
    xmlparser = etree.XMLPullParser(["start", "end", "start-ns"])
    handler = Envelope(workbasket_status=status, tamato_username=username,)

    while True:
        buffer = taric3_file.read(XML_CHUNK_SIZE)
        if buffer == "":
            break
        xmlparser.feed(buffer)
        for event, elem in xmlparser.read_events():
            if event == "start":
                handler.start(elem)

            if event == "start_ns":
                nsmap.update([elem])

            if event == "end":
                handler.end(elem)


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric3_file", help="The TARIC3 file to be parsed.", type=str,
        )
        parser.add_argument(
            "-u",
            "--username",
            help="The username to use for the owner of the workbaskets created.",
            type=str,
        )
        parser.add_argument(
            "-s",
            "--status",
            choices=[
                WorkflowStatus.NEW_IN_PROGRESS.value,
                WorkflowStatus.AWAITING_APPROVAL.value,
                WorkflowStatus.READY_FOR_EXPORT.value,
                WorkflowStatus.PUBLISHED.value,
            ],
            help="The status of the workbaskets containing the import changes.",
            type=str,
        )

    def handle(self, *args, **options):
        with open(options["taric3_file"]) as taric3_file:
            import_taric(
                taric3_file=taric3_file,
                username=options["username"],
                status=options["status"],
            )
