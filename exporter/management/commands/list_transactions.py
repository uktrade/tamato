import sys

from django.core.management import BaseCommand
from django.db.transaction import atomic

from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Command(BaseCommand):
    """
    Dump envelope to file or stdout.

    Invalid envelopes are output but with error level set.
    """

    help = "List workbaskets with status QUEUED."

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
        workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.QUEUED)
        if not workbaskets:
            self.stdout.write("No workbaskets with status QUEUED.")

        # transactions:  will be serialized, then added to an envelope for uploaded.
        transactions = workbaskets.ordered_transactions()

        if not transactions:
            sys.exit(
                f"Nothing to upload:  {workbaskets.count()} Workbaskets QUEUED but none contain any transactions.",
            )

        self.stdout.write(f"{workbaskets.count()}  Workbaskets ready for export")
        self.stdout.write("    id:  transactions:")
        for workbasket in workbaskets:
            self.stdout.write(
                f"{workbasket.pk: >6}   {workbasket.transactions.all().count()}",
            )
