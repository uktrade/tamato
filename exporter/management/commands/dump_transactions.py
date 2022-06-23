import ast
import itertools
import os
import sys

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic
from lxml import etree

from common.serializers import validate_envelope
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from exporter.util import item_timer
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
            help="Override first envelope id [6 digit number] or auto for to use the next available.",
            type=str,
            default="auto",
            action="store",
            nargs=1,
        )

        parser.add_argument(
            "-d",
            "--dir",
            dest="directory",
            default=".",
            help="Directory to output to, defaults to the current directory.",
        )

        parser.add_argument(
            "workbasket_ids",
            help=(
                "Override the default selection of APPROVED workbaskets "
                "with a comma-separated list of workbasket ids."
            ),
            nargs="*",
            type=ast.literal_eval,
            default=None,
            action="store",
        )

        parser.add_argument(
            "--max-envelope-size",
            help=f"Set the maximum envelope size in bytes, defaults to settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE [{settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE}].",
            type=int,
            default=settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE,
            action="store",
        )

        parser.add_argument(
            "--disable-splitting",
            help="Do not split envelopes larger than MAX_ENVELOPE_SIZE, overrides --max-envelope-size.",
            default=False,
            action="store_true",
        )

    @atomic
    def handle(self, *args, **options):
        workbasket_ids = options.get("workbasket_ids")
        if workbasket_ids:
            query = dict(id__in=itertools.chain.from_iterable(workbasket_ids))
        else:
            query = dict(status=WorkflowStatus.APPROVED)

        workbaskets = WorkBasket.objects.filter(**query)
        if not workbaskets:
            sys.exit("Nothing to upload:  No workbaskets with status APPROVED.")

        # transactions:  will be serialized, then added to an envelope for uploaded.
        transactions = workbaskets.ordered_transactions()

        if not transactions:
            sys.exit(
                f"Nothing to upload:  {workbaskets.count()} Workbaskets APPROVED but none contain any transactions.",
            )

        if options.get("envelope_id") == ["auto"]:
            envelope_id = int(Envelope.next_envelope_id())
        else:
            envelope_id = int(options.get("envelope_id")[0])

        # Setting max_envelope_size to 0, also disables splitting - so normalise 0 to None:
        max_envelope_size = (
            None
            if options.get("disable_splitting")
            else int(options.get("max_envelope_size") or None)
        )

        directory = options.get("directory", ".")

        output_file_constructor = dit_file_generator(directory, envelope_id)
        serializer = MultiFileEnvelopeTransactionSerializer(
            output_file_constructor,
            envelope_id=envelope_id,
            max_envelope_size=max_envelope_size,
        )
        errors = False
        for time_to_render, rendered_envelope in item_timer(
            serializer.split_render_transactions(transactions),
        ):
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
                        f"{envelope_file.name} \N{WHITE HEAVY CHECK MARK}  XML valid.  {total_transactions} transactions, serialized in {time_to_render:.2f} seconds using {envelope_file.tell()} bytes.",
                    )
        if errors:
            sys.exit(1)
