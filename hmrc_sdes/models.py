import uuid
from datetime import datetime
from typing import Optional

from django.db import models
from django.utils import timezone
from storages.backends.s3boto3 import S3Boto3Storage

from hmrc_sdes.api_client import HmrcSdesClient


def to_hmrc(instance: "Upload"):
    """Generate the filepath to upload to HMRC"""

    return f"tohmrc/staging/DIT{instance.envelope.envelope_id}.xml"


class Upload(models.Model):
    """Represents a TARIC differential update file upload to HMRC"""

    file = models.FileField(storage=S3Boto3Storage, upload_to=to_hmrc)
    envelope = models.ForeignKey("taric.Envelope", on_delete=models.PROTECT)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    checksum = models.CharField(max_length=32, editable=False)
    notification_sent = models.DateTimeField(editable=False, null=True)

    def notify_hmrc(self, now: Optional[datetime]):
        client = HmrcSdesClient()
        client.notify_transfer_ready(self)

        if now is None:
            now = timezone.now()
        self.notification_sent = now
        self.save()

    @property
    def filename(self):
        return f"{str(self.envelope)}.xml"

    @property
    def notification_payload(self):
        return {
            "informationType": "EDM",
            "correlationID": self.correlation_id,
            "file": {
                "fileName": self.filename,
                "fileSize": self.file.size,
                "checksum": self.checksum,
                "checksumAlgorithm": "MD5",
            },
        }
