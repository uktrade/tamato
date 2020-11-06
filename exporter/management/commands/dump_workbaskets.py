import sys


from django.core.management import BaseCommand

from exporter.management.commands.util import (
    get_envelope_of_active_workbaskets,
    validate_envelope_xml,
)
from workbaskets.validators import WorkflowStatus
from workbaskets.models import WorkBasket


class Command(BaseCommand):
    help = "Output workbaskets ready for export to a file or stdout."

    def add_arguments(self, parser):
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
            return sys.stdout.buffer
        return open(filename, "wb+")

    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.prefetch_ordered_tracked_models().filter(
            status=WorkflowStatus.READY_FOR_EXPORT
        )

        envelope = get_envelope_of_active_workbaskets(workbaskets)
        if not validate_envelope_xml(envelope):
            sys.exit(f"Envelope did not validate against XSD")

        with self.get_output_file(options["filename"]) as f:
            f.write(envelope)
