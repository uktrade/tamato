import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import FileField
from django.db.models import Manager
from django.db.models import QuerySet
from django.db.transaction import atomic
from lxml import etree

from common.models.mixins import TimestampedMixin
from common.serializers import validate_envelope
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from publishing.models.packaged_workbasket import PackagedWorkBasket
from publishing.models.state import ProcessingState
from publishing.storages import EnvelopeStorage
from taric import validators
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

# Exceptions
class EnvelopeCurrentlyProccessing(Exception):
    pass


class EnvelopeInvalidQueuePosition(Exception):
    pass


class EnvelopeNoTransactions(Exception):
    pass


class EnvelopeManager(Manager):
    @atomic
    def create(self, packaged_work_basket, **kwargs):
        """
        Create a new instance, from the packaged workbasket at the front of the
        queue.

         :param packaged_work_basket: packaged workbasket to upload.
        @throws EnvelopeCurrentlyProccessing if an envelope is currently being processed
        @throws EnvelopeInvalidQueuePosition if the packaged workbasket is not
        a the front of the queue
        """
        currently_processing = PackagedWorkBasket.objects.currently_processing()
        if currently_processing:
            raise EnvelopeCurrentlyProccessing(
                "Unable to create Envelope,"
                f"({currently_processing}) is currently proccessing",
            )

        if packaged_work_basket.position != 1:
            raise EnvelopeInvalidQueuePosition(
                "Unable to create Envelope,"
                f"({packaged_work_basket.workbasket}) is not at the front of the queue",
            )

        envelope_id = Envelope.next_envelope_id()
        envelope = super().create(envelope_id=envelope_id, **kwargs)
        envelope.upload_envelope(
            packaged_work_basket.workbasket,
        )
        return envelope


class EnvelopeQuerySet(QuerySet):
    def for_year(self, year: Optional[int] = None):
        """
        Return all envelopes for a year, defaulting to this year.

        :param year: int year, defaults to this year.
        Limitation:  This queries envelope_id which only stores two digit dates.
        """
        if year is None:
            now = datetime.today()
        else:
            now = datetime(year, 1, 1)

        return self.filter(envelope_id__regex=rf"{now:%y}\d{{4}}").order_by(
            "envelope_id",
        )


class EnvelopeId(CharField):
    """An envelope ID must match the format YYxxxx, where YY is the last two
    digits of the current year and xxxx is a zero padded integer, incrementing
    from 0001 for the first envelope of the year."""

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        kwargs["validators"] = [validators.EnvelopeIdValidator]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["validators"]
        return name, path, args, kwargs


class Envelope(TimestampedMixin):
    """
    Represents an automated packaged envelope.

    An Envelope contains one or more Transactions, listing changes to be applied
    to the tariff in the sequence defined by the transaction IDs. Contains
    xml_file which is a reference to the envelope stored on s3
    """

    class Meta:
        ordering = ("envelope_id",)

    objects: EnvelopeQuerySet = EnvelopeManager.from_queryset(
        EnvelopeQuerySet,
    )()

    envelope_id = EnvelopeId()
    xml_file = FileField(storage=EnvelopeStorage, default="")
    deleted = BooleanField(default=False)
    """marks an envelope as deleted within contexts where an instance can not be immediately deleted from the DB."""

    @classmethod
    def next_envelope_id(cls):
        """Get packaged workbaskets where proc state SUCCESS."""
        envelope = (
            Envelope.objects.for_year()
            .filter(
                packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
            )
            .last()
        )

        if envelope is None:
            # First envelope of the year.
            now = datetime.today()
            counter = max(1, int(settings.HMRC_PACKAGING_SEED_ENVELOPE_ID))
        else:
            year = int(envelope.envelope_id[:2])
            counter = max(
                int(envelope.envelope_id[2:]) + 1,
                int(settings.HMRC_PACKAGING_SEED_ENVELOPE_ID),
            )

            if counter > 9999:
                raise ValueError(
                    "Cannot create more than 9999 Envelopes on a single year.",
                )

            now = datetime(year, 1, 1)

        return f"{now:%y}{counter:04d}"

    def delete_envelope(self, **kwargs):
        """delete function within model to ensure that the file is deleted from
        s3 and then set the delete flag in the model."""
        self.xml_file.delete()
        self.deleted = True

    @atomic
    def upload_envelope(
        self,
        workbasket,
    ):
        """
        Upload Envelope data to the s3 bucket and return artifacts for the
        database.

        Side effects on success: Create Xml file and upload envelope XML to an
        S3 object.
        """

        filename = f"DIT{str(self.envelope_id)}.xml"

        # transactions: will be serialized, then added to an envelope for upload.
        workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
        transactions = workbaskets.ordered_transactions()

        if not transactions:
            msg = f"transactions to upload:  {transactions.count()} does not contain any transactions."
            logger.info(msg)
            raise EnvelopeNoTransactions(msg)

        # Envelope XML is written to temporary files for validation before anything is created
        # in the database or uploaded to s3.
        with tempfile.TemporaryDirectory(prefix="dit-tamato_") as temporary_directory:
            output_file_constructor = dit_file_generator(
                temporary_directory,
                int(self.envelope_id),
            )

            serializer = MultiFileEnvelopeTransactionSerializer(
                output_file_constructor,
                envelope_id=self.envelope_id,
            )

            rendered_envelope = list(
                serializer.split_render_transactions(transactions),
            )[0]
            logger.info(f"rendered_envelope {rendered_envelope}")
            envelope_file = rendered_envelope.output
            if not rendered_envelope.transactions:
                msg = f"{envelope_file.name}  is empty !"
                logger.error(msg)
                raise EnvelopeNoTransactions(msg)
            # Transaction envelope data XML is valid, ready for upload to s3
            else:
                envelope_file.seek(0, os.SEEK_SET)
                try:
                    validate_envelope(envelope_file)
                except etree.DocumentInvalid:
                    logger.error(f"{envelope_file.name}  is Envelope invalid !")
                    raise
                else:
                    envelope_file.seek(0, os.SEEK_SET)
                    content_file = ContentFile(envelope_file.read())
                    self.xml_file = content_file

                    envelope_file.seek(0, os.SEEK_SET)

                    self.xml_file.save(filename, content_file)

                    logger.info("Workbasket saved to CDS S3 bucket")
                    logger.debug("Uploaded: %s", filename)

    def __repr__(self):
        return f'<Envelope: envelope_id="{self.envelope_id}">'
