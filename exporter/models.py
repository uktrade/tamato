import uuid
from datetime import datetime
from typing import Optional

from django.db import models
from django.utils import timezone
from storages.backends.s3boto3 import S3Boto3Storage

from hmrc_sdes.api_client import HmrcSdesClient
from taric.models import Envelope


def to_hmrc(instance: "Upload"):
    """Generate the filepath to upload to HMRC."""

    return f"tohmrc/staging/{instance.filename}"


class Upload(models.Model):
    """Represents a TARIC differential update file upload to HMRC."""

    file = models.FileField(storage=S3Boto3Storage, upload_to=to_hmrc)
    envelope = models.ForeignKey(Envelope, on_delete=models.PROTECT)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    checksum = models.CharField(max_length=32, editable=False)
    notification_sent = models.DateTimeField(editable=False, null=True)

    # Max size is 50 megabytes
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def notify_hmrc(self, now: Optional[datetime] = None):
        client = HmrcSdesClient()
        client.notify_transfer_ready(self)

        if now is None:
            now = timezone.now()
        self.notification_sent = now
        self.save()

    @property
    def filename(self):
        return f"DIT{str(self.envelope.envelope_id)}.xml"

    @property
    def notification_payload(self):
        return {
            "informationType": "EDM",
            "correlationID": str(self.correlation_id),
            "file": {
                "fileName": self.filename,
                "fileSize": self.file.size,
                "checksum": self.checksum,
                "checksumAlgorithm": "MD5",
            },
        }
