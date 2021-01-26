import sys

from django.db.transaction import atomic

from exporter.management.commands.util import (
    TransactionsBaseCommand,
)
from exporter.management.util import serialize_envelope_as_xml
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Command(TransactionsBaseCommand):
    """Dump envelope to file or stdout.

    Invalid envelopes are output but with error level set.
    """

    help = "Output workbaskets ready for export to a file or stdout"

    def add_arguments(self, parser):
        parser.add_argument(
            "envelope_id",
            help="The 6-digit envelope ID to use on the generated envelope.",
            type=int,
        )
        parser.add_argument(
            "-o",
            "--output",
            dest="filename",
            help="File to output to, - for stdout.",
            default="-",
        )

    def get_output_file(self, filename):
        """Enable the standard where '-' refers to stdout, every other string is an actual filename."""
        if filename == "-":
            return self.stdout
        return open(filename, "w+")

    @atomic
    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.READY_FOR_EXPORT)
        if not workbaskets:
            sys.exit("No workbaskets with status READY_FOR_EXPORT.")

        envelope = workbaskets.envelope_of_transactions()
        envelope_data = serialize_envelope_as_xml(envelope)

        f = self.get_output_file(options["filename"])
        f.write(envelope_data.decode("utf-8"))
        if f not in (self.stdout, self.stderr):
            # Closing stdout or stderr can make a capturing pytest unhappy.
            f.close()

        # Don't add more output here in case output is stdout.
        self.validate_envelope(envelope_data)
