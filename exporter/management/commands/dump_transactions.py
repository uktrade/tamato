from exporter.management.commands.util import get_envelope_of_active_workbaskets
from exporter.management.commands.util import WorkBasketBaseCommand
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Command(WorkBasketBaseCommand):
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

    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.READY_FOR_EXPORT)

        envelope = get_envelope_of_active_workbaskets(
            options["envelope_id"], workbaskets
        )

        f = self.get_output_file(options["filename"])
        f.write(envelope.decode("utf-8"))
        if f not in (self.stdout, self.stderr):
            # Closing stdout or stderr can make a capturing pytest unhappy.
            f.close()

        # Don't add more output here in case we are outputting to stdout.
        self.validate_envelope(envelope)
