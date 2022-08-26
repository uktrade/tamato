import ast
import itertools
import sys

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic

from exporter.management.commands.util import dump_transactions
from taric.models import Envelope
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


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

        success = dump_transactions(
            transactions,
            envelope_id,
            directory,
            max_envelope_size,
            self.stdout,
        )
        if success:
            sys.exit(1)
