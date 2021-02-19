import io
import os
import sys

from django.core.management import BaseCommand
from django.db.transaction import atomic

from exporter.management.commands.util import StdOutStdErrContext
from exporter.tasks import validate_envelope
from importer.management.commands.utils import EnvelopeSerializer
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Command(BaseCommand):
    """Dump envelope to file or stdout.

    Invalid envelopes are output but with error level set.
    """

    help = "Output workbaskets ready for export to a file or stdout"

    def add_arguments(self, parser):
        parser.add_argument(
            "envelope_id",
            help="The 6-digit envelope ID to use on the generated envelope.",
            type=int,
            default=None,
            nargs="?",
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
            return StdOutStdErrContext(self.stdout)
        return open(filename, "w+")

    @atomic
    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.READY_FOR_EXPORT)
        if not workbaskets:
            sys.exit("No workbaskets with status READY_FOR_EXPORT.")

        tracked_models = workbaskets.ordered_tracked_models()
        if not tracked_models:
            sys.exit(
                f"{workbaskets.count()} Workbaskets READY_FOR_EXPORT but none contain any transactions."
            )

        envelope_id = None
        if options.get("envelope_id") is not None:
            envelope_id = int(options["envelope_id"])

        # Write to a buffer so that data can be validated on non seekable output such as stdout.
        buffer = io.StringIO()
        with EnvelopeSerializer(buffer, envelope_id=envelope_id, newline=True) as env:
            env.render_transaction(tracked_models)

        with self.get_output_file(options["filename"]) as output_file:
            output_file.write(buffer.getvalue())

        buffer.seek(os.SEEK_SET)
        validate_envelope(buffer, skip_declaration=True)
