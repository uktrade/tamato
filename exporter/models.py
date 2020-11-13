import json
import uuid
from datetime import datetime
from typing import Optional

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from storages.backends.s3boto3 import S3Boto3Storage

from common.models import TimestampedMixin
from hmrc_sdes.api_client import HmrcSdesClient
from taric import validators


class Transaction(TimestampedMixin):
    def to_json(self):
        """Used for serializing to the session"""

        data = {key: val for key, val in self.__dict__.items() if key != "_state"}
        return json.dumps(data, cls=DjangoJSONEncoder)


class EnvelopeId(models.CharField):
    """An envelope ID must match the format YYxxxx, where YY is the last two digits of
    the current year and xxxx is a zero padded integer, incrementing from 0001 for the
    first envelope of the year.
    """

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        kwargs["validators"] = [validators.EnvelopeIdValidator]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["validators"]
        return name, path, args, kwargs


class Envelope(models.Model):
    """Represents a TARIC3 envelope

    An Envelope contains one or more Transactions, listing changes to be applied to the
    tariff in the sequence defined by the transaction IDs.
    """

    # Max size is 50 megabytes
    MAX_FILE_SIZE = 50 * 1024 * 1024

    envelope_id = EnvelopeId()
    transactions = models.ManyToManyField(
        Transaction, related_name="envelopes", through="EnvelopeTransaction"
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"DIT{self.envelope_id}"


class EnvelopeTransaction(models.Model):
    """Applies a sequence to Transactions contained in an Envelope."""

    index = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT)
    envelope = models.ForeignKey(Envelope, on_delete=models.PROTECT)


def to_hmrc(instance: "Upload"):
    """Generate the filepath to upload to HMRC"""

    return f"tohmrc/staging/DIT{instance.envelope.envelope_id}.xml"


class Upload(models.Model):
    """Represents a TARIC differential update file upload to HMRC"""

    file = models.FileField(storage=S3Boto3Storage, upload_to=to_hmrc)
    envelope = models.ForeignKey("exporter.Envelope", on_delete=models.PROTECT)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    checksum = models.CharField(max_length=32, editable=False)
    notification_sent = models.DateTimeField(editable=False, null=True)

    def notify_hmrc(self, now: Optional[datetime] = None):
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
            "correlationID": str(self.correlation_id),
            "file": {
                "fileName": self.filename,
                "fileSize": self.file.size,
                "checksum": self.checksum,
                "checksumAlgorithm": "MD5",
            },
        }
