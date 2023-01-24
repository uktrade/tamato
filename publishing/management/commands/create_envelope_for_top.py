from django.core.management import BaseCommand

from publishing.models.packaged_workbasket import PackagedWorkBasket


class Command(BaseCommand):
    help = (
        "Generate an envelope for the top-most packaged workbasket. Note that "
        "if a workbasket is currently being processed, then this command will "
        "fail in order to preserve envelope content and ID integrity."
    )

    def handle(self, *args, **options):
        PackagedWorkBasket.create_envelope_for_top()
