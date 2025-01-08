import sys

from django.core.management import BaseCommand

from publishing.models import CrownDependenciesEnvelope
from publishing.models import PackagedWorkBasket
from publishing.tasks import publish_to_api


class Command(BaseCommand):
    help = (
        "Manage envelope uploads to Tariff API. Without arguments, this "
        "management command lists unpublished envelopes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--publish-async",
            action="store_true",
            help=(
                "Asynchronously run (via a Celery task) the function to "
                "upload unpublished envelopes to the tariffs-api service."
            ),
        )
        parser.add_argument(
            "--publish-now",
            action="store_true",
            help=(
                "Immediately run (within the current terminal's process) the "
                "function to upload unpublished envelopes to the tariffs-api "
                "service."
            ),
        )

    def get_incomplete_envelopes(self):
        return CrownDependenciesEnvelope.objects.unpublished()

    def get_unpublished_envelopes(self):
        return PackagedWorkBasket.objects.get_unpublished_to_api()

    def print_envelope_details(self, position, envelope):
        self.stdout.write(
            f"position={position}, pk={envelope.pk}, envelope_id={envelope.envelope_id}",
        )

    def list_unpublished_envelopes(self):
        incomplete = self.get_incomplete_envelopes()
        unpublished = self.get_unpublished_envelopes()
        if incomplete:
            self.stdout.write(
                f"{incomplete.count()} envelope(s) not completed publishing:",
            )
            for i, crowndependencies in enumerate(incomplete, start=1):
                self.print_envelope_details(
                    position=i,
                    envelope=crowndependencies.packagedworkbaskets.last().envelope,
                )
        if unpublished:
            self.stdout.write(
                f"{unpublished.count()} envelope(s) ready to be published in the following order:",
            )
            for i, packaged_work_basket in enumerate(unpublished, start=1):
                self.print_envelope_details(
                    position=i,
                    envelope=packaged_work_basket.envelope,
                )

    def publish(self, now: bool):
        if self.get_unpublished_envelopes() or self.get_incomplete_envelopes():
            if now:
                self.stdout.write(f"Calling `publish_to_api()` now.")
                publish_to_api()
            else:
                self.stdout.write(f"Calling `publish_to_api()` asynchronously.")
                publish_to_api.apply()
        else:
            sys.exit("No unpublished envelopes")

    def handle(self, *args, **options):
        if options["publish_async"] or options["publish_now"]:
            self.publish(now=options["publish_now"])
        else:
            self.list_unpublished_envelopes()
