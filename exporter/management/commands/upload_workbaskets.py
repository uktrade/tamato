from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from exporter.management.commands.util import (
    get_envelope_of_active_workbaskets,
    get_envelope_filename,
    WorkBasketBaseCommand,
)
from exporter.storages import HMRCStorage
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class Command(WorkBasketBaseCommand):
    """Upload envelope to HMRC s3 storage.

    Invalid envelopes are NOT uploaded.
    """

    help = "Upload workbaskets ready for export to HMRC S3 Storage."

    def handle(self, *args, **options):
        workbaskets = WorkBasket.objects.prefetch_ordered_tracked_models().filter(
            status=WorkflowStatus.READY_FOR_EXPORT
        )

        envelope = get_envelope_of_active_workbaskets(workbaskets)
        self.validate_envelope(envelope)

        filename = get_envelope_filename(1)
        full_filename = str(Path(settings.HMRC_UPLOAD_DIR) / filename)

        content_file = ContentFile(envelope)
        storage = HMRCStorage()
        destination = storage.save(full_filename, content_file)
        print(f"Uploaded: {destination}")
