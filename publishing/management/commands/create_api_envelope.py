import itertools
import sys

from django.core.management import BaseCommand

from publishing.models import PackagedWorkBasket


class Command(BaseCommand):
    help = "Create TAPApiEnvelope for successfully-processed, packaged workbaskets that do not have a published envelope and API envelope."

    def add_arguments(self, parser):
        parser.add_argument(
            "-l",
            "--list",
            dest="list",
            action="store_true",
            help="List packaged workbaskets for which an API envelope can be created.",
        )
        parser.add_argument(
            "-n",
            "--number",
            dest="number",
            type=int,
            nargs=1,
            action="store",
            help="How many packaged workbaskets for which to create an API envelope.",
        )

    def get_packaged_workbaskets(self):
        packaged_workbaskets = PackagedWorkBasket.objects.get_unpublished_to_api()
        if not packaged_workbaskets:
            sys.exit(
                "No packaged workbaskets available that are successfully processed and without a published envelope and API envelope",
            )
        return packaged_workbaskets

    def list_packaged_workbaskets(self):
        packaged_workbaskets = self.get_packaged_workbaskets()
        self.stdout.write(
            f"{packaged_workbaskets.count()} packaged workbasket(s) for which an API envelope can be created in the following order:",
        )
        for i, pwb in enumerate(packaged_workbaskets, start=1):
            self.stdout.write(f"{i}: {pwb}")

    def handle(self, *args, **options):
        if options["list"]:
            self.list_packaged_workbaskets()
            return

        packaged_workbaskets = self.get_packaged_workbaskets()
        creation_count = options.get("number")
        if creation_count:
            for pwb in itertools.islice(packaged_workbaskets, creation_count[0]):
                pwb.create_api_publishing_envelope()
        else:
            for pwb in packaged_workbaskets:
                pwb.create_api_publishing_envelope()
