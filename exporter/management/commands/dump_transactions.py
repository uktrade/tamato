import logging
import os
import sys

from django.conf import settings
from django.core.management import BaseCommand
from django.db.transaction import atomic
from lxml import etree

from common.models import Transaction
from common.models.utils import override_current_transaction
from common.serializers import validate_envelope
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from exporter.util import item_timer
from taric.models import Envelope
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

# VARIATION_SELECTOR enables emoji presentation
WARNING_SIGN_EMOJI = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"

logger = logging.getLogger(__name__)


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
                "Override the default selection of 'all workbaskets with status APPROVED'"
                "with a comma-separated list of workbasket ids."
            ),
            nargs="*",
            type=int,
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

        parser.add_argument(
            "--replay",
            help="Output transactions as at the time the workbasket was published, by setting current_transaction to "
            "one before the specified workbasket.",
            action="store_true",
        )

    @atomic
    def handle(self, *args, **options):
        workbasket_ids = options.get("workbasket_ids")
        if workbasket_ids:
            query = dict(id__in=workbasket_ids)
        else:
            query = dict(status=WorkflowStatus.APPROVED)

        workbaskets = WorkBasket.objects.filter(**query)
        if not workbaskets:
            sys.exit("Nothing to upload:  No workbaskets with status APPROVED.")

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

        # 'replay' sets the current transaction to the one 'before' the specified workbasket
        # to allow the system to export the data as it was when the workbasket was first published.
        replay_from_tx = None
        if options.get("replay"):
            replay_from_tx = Transaction.objects.filter(
                pk=transactions[0].pk - 1,
            ).last()

        if replay_from_tx is None:
            # No replay, just serialize the transactions.
            if not self.do_serialize_envelopes(
                directory,
                envelope_id,
                max_envelope_size,
                transactions,
            ):
                sys.exit(1)
        else:
            # Simulate latest_transaction being set to replay_from_tx
            if not set(
                workbaskets.values_list("status", flat=True).distinct(),
            ).issubset(WorkflowStatus.approved_statuses()):
                sys.exit(
                    "Replay only applies to approved workbaskets.",
                )

            with override_current_transaction(replay_from_tx):
                logging.debug("Replay from transaction: %s", replay_from_tx)
                if not self.do_serialize_envelopes(
                    directory,
                    envelope_id,
                    max_envelope_size,
                    transactions,
                ):
                    sys.exit(1)

    def do_serialize_envelopes(
        self,
        directory,
        envelope_id,
        max_envelope_size,
        transactions,
    ):
        """
        Serialize transactions to a series of files.

        :return: True if no errors occurred.
        """
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
                        f"{envelope_file.name} {WARNING_SIGN_EMOJI} ️ XML invalid.",
                    )
                else:
                    total_transactions = len(rendered_envelope.transactions)
                    self.stdout.write(
                        f"{envelope_file.name} \N{WHITE HEAVY CHECK MARK}  XML valid.  {total_transactions} transactions, serialized in {time_to_render:.2f} seconds using {envelope_file.tell()} bytes.",
                    )
        return not errors
