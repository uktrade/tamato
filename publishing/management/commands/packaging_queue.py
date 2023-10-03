from django.core.management import BaseCommand
from django.db.transaction import atomic

from publishing.models import Envelope
from publishing.models import PackagedWorkBasket
from publishing.models.packaged_workbasket import ProcessingState


class Command(BaseCommand):
    help = (
        "View and manage the packaging queue. The bare command prints the "
        "state of queued PackageWorkBasket instances, including those in both "
        "that have state AWAITING_PROCESSING. Instances in state "
        "CURRENTLY_PROCESSING will be unchanged to avoid surprises for queue "
        "consumers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-positions",
            default=False,
            action="store_true",
            help=(
                "Reset the position of each queued PackagedWorkBasket instance "
                "that has state AWAITING_PROCESSING. Instances in state "
                "CURRENTLY_PROCESSING will be unchanged to avoid surprises for "
                "queue consumers - these should be rejected in the "
                "conventional manner via the user interface."
            ),
        )

    def print_queue(self):
        """Print out details of all currently packaged queued workbaskets,
        including those with a `processing_state` of `AWAITING_PROCESSING` or
        `CURRENTLY_PROCESSING`."""

        queued_pw_qs = PackagedWorkBasket.objects.all_queued()

        for pw in queued_pw_qs:
            envelope_pk = pw.envelope.pk if pw.envelope else None

            self.stdout.write(f"@ position: {pw.position},")
            self.stdout.write(f"  processing_state: {pw.processing_state},")
            self.stdout.write(f"  pk: {pw.pk},")
            self.stdout.write(f"  workbasket.pk: {pw.workbasket.pk},")
            self.stdout.write(f"  envelope.pk: {envelope_pk},")
            if pw.envelope:
                e = pw.envelope
                self.stdout.write(f"  envelope.envelope_id: {e.envelope_id},")
                self.stdout.write(f"  envelope.xml_file: {e.xml_file},")
                self.stdout.write(f"  envelope.deleted: {e.deleted},")

    @atomic
    def reset_queue_positions(self):
        """Brute-force reset the `position` attribute of all PackagedWorkBasket
        instances with `processing_state = AWAITING_PROCESSING`."""

        packaged_workbaskets = PackagedWorkBasket.objects.filter(
            processing_state=ProcessingState.AWAITING_PROCESSING,
        )
        self.stdout.write(
            f"Resetting the positions of {packaged_workbaskets.count()} "
            f"PackagedWorkBasket instance(s).",
        )
        self.stdout.write()

        processing_envelopes = PackagedWorkBasket.objects.filter(
            processing_state=ProcessingState.CURRENTLY_PROCESSING,
        )
        processing_envelopes_count = processing_envelopes.count()
        if processing_envelopes_count:
            self.stdout.write(
                f"{processing_envelopes_count} PackagedWorkBasket instance(s) "
                f"with processing_state set to CURRENTLY_PROCESSING will be "
                f"unchanged - they should be managed via the TAP UI.",
            )
            self.stdout.write()

        associated_envelopes = []
        current_position = 1
        for pw in packaged_workbaskets:
            pw.position = current_position
            current_position += 1
            if pw.envelope:
                associated_envelopes.append(pw.envelope)

        PackagedWorkBasket.objects.bulk_update(
            packaged_workbaskets,
            ["position"],
        )

        if associated_envelopes:
            self.stdout.write(
                f"Deleting {len(associated_envelopes)} Envelope instance(s) "
                f"associated with re-positioned PackagedWorkBaskets. ",
            )
            self.stdout.write()
            self.stdout.write(
                f"It may be necessary to re-generated the top-most envelope in "
                f"the queue.",
            )
            Envelope.objects.filter(
                pk__in=[e.pk for e in associated_envelopes],
            ).delete()
        else:
            self.stdout.write(
                f"No Envelope instances were associated with the repositioned "
                f"PackagedWorkBasket instances.",
            )

        self.stdout.write()

    def handle(self, *args, **options):
        if options.get("reset_positions"):
            self.reset_queue_positions()

        self.stdout.write("All queued PackagedWorkBasket instances:")
        self.print_queue()
