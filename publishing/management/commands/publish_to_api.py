import sys

from django.core.management import BaseCommand

from publishing.models import CrownDependenciesEnvelope
from publishing.models import PackagedWorkBasket
from publishing.tasks import publish_to_api


class Command(BaseCommand):
    help = "Upload unpublished envelopes to the Tariff API."

    def add_arguments(self, parser):
        parser.add_argument(
            "-l",
            "--list",
            dest="list",
            action="store_true",
            help="List unpublished envelopes.",
        )

    def get_incomplete_envelopes(self):
        incomplete = CrownDependenciesEnvelope.objects.unpublished()
        if not incomplete:
            sys.exit("No incomplete envelopes")
        return incomplete

    def get_unpublished_envelopes(self):
        unpublished = PackagedWorkBasket.objects.get_unpublished_to_api()
        if not unpublished:
            sys.exit("No unpublished envelopes")
        return unpublished

    def list_unpublished_envelopes(self):
        incomplete = self.get_incomplete_envelopes()
        unpublished = self.get_unpublished_envelopes()
        if incomplete:
            self.stdout.write(
                f"{incomplete.count()} envelope(s) not completed publishing:",
            )
            for i, crowndependencies in enumerate(incomplete, start=1):
                self.stdout.write(
                    f"{i}: {crowndependencies.packagedworkbaskets.last().envelope}",
                )
        self.stdout.write(
            f"{unpublished.count()} envelope(s) ready to be published in the following order:",
        )
        for i, packaged_work_basket in enumerate(unpublished, start=1):
            self.stdout.write(f"{i}: {packaged_work_basket.envelope}")

    def handle(self, *args, **options):
        if options["list"]:
            self.list_unpublished_envelopes()
            return

        if self.get_unpublished_envelopes() or self.get_incomplete_envelopes():
            publish_to_api.apply()
