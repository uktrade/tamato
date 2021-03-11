import os
import sys

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic
from lxml import etree

from common.serializers import validate_envelope
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from taric.models import Envelope
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

# VARIATION_SELECTOR enables emoji presentation
WARNING_SIGN_EMOJI = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"


class Command(BaseCommand):
    """
    Dump envelope to file or stdout.

    Invalid envelopes are output but with error level set.
    """

    help = "Dump transactions ready for export to a directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "envelope_id",
            help="Override first envelope id [6 digit number].",
            type=int,
            default=None,
            action="store",
            nargs="?",
        )

        parser.add_argument(
            "-d",
            "--dir",
            dest="directory",
            default=".",
            help="Directory to output to, defaults to the current directory.",
        )

    @atomic
    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.READY_FOR_EXPORT)
        if not workbaskets:
            sys.exit("Nothing to upload:  No workbaskets with status READY_FOR_EXPORT.")

        # transactions:  will be serialized, then added to an envelope for uploaded.
        transactions = workbaskets.ordered_transactions()

        if not transactions:
            sys.exit(
                f"Nothing to upload:  {workbaskets.count()} Workbaskets READY_FOR_EXPORT but none contain any transactions.",
            )

        if options.get("envelope_id") is not None:
            envelope_id = int(options.get("envelope_id"))
        else:
            envelope_id = int(Envelope.next_envelope_id())

        directory = options.get("directory", ".")

        output_file_constructor = dit_file_generator(directory, envelope_id)
        serializer = MultiFileEnvelopeTransactionSerializer(
            output_file_constructor,
            envelope_id=envelope_id,
            max_envelope_size=settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE,
        )
        errors = False
        for rendered_envelope in serializer.split_render_transactions(transactions):
            envelope_file = rendered_envelope.output
            if not rendered_envelope.transactions:
                self.stdout.write(
                    f"{envelope_file.name} {WARNING_SIGN_EMOJI}  is empty !",
                )
                errors = True
            else:
                envelope_file.seek(0, os.SEEK_SET)
                try:
                    validate_envelope(envelope_file)
                except etree.DocumentInvalid:
                    self.stdout.write(
                        f"{envelope_file.name} {WARNING_SIGN_EMOJI}️ Envelope invalid:",
                    )
                else:
                    total_transactions = len(rendered_envelope.transactions)
                    self.stdout.write(
                        f"{envelope_file.name} \N{WHITE HEAVY CHECK MARK}  XML valid.  {total_transactions} transactions in {envelope_file.tell()} bytes.",
                    )
        if errors:
            sys.exit(1)
