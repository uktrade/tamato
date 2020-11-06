from django.core.files.base import ContentFile

from exporter.management.commands.util import (
    get_envelope_of_active_workbaskets,
    validate_envelope_xml,
    get_envelope_filename,
)
from exporter.storages import get_hmrc_storage
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

import sys
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Upload workbaskets ready for export to HMRC S3 Storage."

    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.prefetch_ordered_tracked_models().filter(
            status=WorkflowStatus.READY_FOR_EXPORT
        )

        envelope = get_envelope_of_active_workbaskets(workbaskets)
        if not validate_envelope_xml(envelope):
            sys.exit(f"Envelope did not validate against XSD")

        filename = get_envelope_filename(1)
        content_file = ContentFile(envelope)
        storage = get_hmrc_storage()
        destination = storage.save(f"tohmrc/staging/{filename}", content_file)
        print(f"Uploaded: {destination}")
