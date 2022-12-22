# XXX need to keep this file for migrations to work. delete later.
import os
import logging
import tempfile
from datetime import date
from typing import Optional
from pathlib import Path
from lxml import etree

from django.core.files.base import ContentFile
from django.db import models
from django.db.models import QuerySet
from django.conf import settings

from common.models.transactions import Transaction
from publishing import models as publishing_models
from taric import validators
from exporter.storages import HMRCStorage
from exporter.util import dit_file_generator
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from common.serializers import validate_envelope

logger = logging.getLogger(__name__)

class EnvelopeCurrentlyProccessing(Exception):
    pass

class EnvelopeInvalidQueuePosition(Exception):
    pass

class WorkBasketNoTransactions(Exception):
    pass

class EnvelopeManager(models.Manager):

    def upload_and_create_envelope(
        self,
        workbasket,
        current_envelope_id,
    ):
        """
        Upload Envelope data to the the s3 and return artifacts for the database.

        Side effects on success:
        Create Xml file and upload envelope XML to an S3 object.

        :return: xml_file
        """

        filename = f"DIT{str(current_envelope_id)}.xml"

        # transactions: will be serialized, then added to an envelope for upload.
        transactions = workbasket.ordered_transactions()

        if not transactions:
            msg = f"transactions to upload:  {transactions.count()} does not contain any transactions."
            logger.info(msg)
            raise WorkBasketNoTransactions(msg)


        # Envelope XML is written to temporary files for validation before anything is created
        # in the database or uploaded to s3.
        with tempfile.TemporaryDirectory(prefix="dit-tamato_") as temporary_directory:
            output_file_constructor = dit_file_generator(
                temporary_directory,
                current_envelope_id,
            )

            serializer = MultiFileEnvelopeTransactionSerializer(
                output_file_constructor,
                envelope_id=current_envelope_id,
                max_envelope_size=settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE,
            )

            rendered_envelope = list(serializer.split_render_transactions(transactions))[0]
            envelope_file = rendered_envelope.output
            if not rendered_envelope.transactions:
                #TODO Raise error
                logger.error(f"{envelope_file.name}  is empty !")
            # Transaction envelope data XML is valid, ready for upload to s3
            try:
                validate_envelope(envelope_file)
            except etree.DocumentInvalid:
                logger.error(f"{envelope_file.name}  is Envelope invalid !")
            else:
                envelope_file.seek(0, os.SEEK_SET)
                           
                content_file = ContentFile(envelope_file.read())
                
                xml_file = content_file

                envelope_file.seek(0, os.SEEK_SET)

                xml_file.save(filename, content_file)

                logger.info("Workbasket saved to CDS S3 bucket")
                logger.debug("Uploaded: %s", filename)
                return xml_file

    def create(self,packaged_work_basket, **kwargs):
        """Create a new instance, from the packaged workbasket at the front of the queue"""
        currently_processing = publishing_models.PackagedWorkBasket.objects.currently_processing()
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

        envelope_id =  Envelope.objects.next_envelope_id()
        xml_file = self.upload_and_create_envelope(
            packaged_work_basket.workbasket,
            envelope_id,
        )
        return super().create(xml_file=xml_file,envelope_id=envelope_id, **kwargs)

class EnvelopeQuerySet(QuerySet):
    def envelopes_by_year(self, year: Optional[int] = None):
        """
        Return all envelopes for a year, defaulting to this year.

        :param year: int year, defaults to this year.

        Limitation:  This queries envelope_id which only stores two digit dates.
        """
        if year is None:
            now = date.today()
        else:
            now = date(year, 1, 1)

        return self.filter(envelope_id__regex=rf"{now:%y}\d{{4}}").order_by(
            "envelope_id",
        )

    def next_envelope_id(self):
        envelope = Envelope.objects.envelopes_by_year().last()

        if envelope is None:
            # First envelope of the year.
            now = date.today()
            counter = 1
        else:
            year = int(envelope.envelope_id[:2])
            counter = int(envelope.envelope_id[2:]) + 1

            if counter > 9999:
                raise ValueError(
                    "Cannot create more than 9999 Envelopes on a single year.",
                )

            now = date(year, 1, 1)

        return f"{now:%y}{counter:04d}"


class EnvelopeId(models.CharField):
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

def to_hmrc(instance: "Envelope", filename: str):
    """Generate the filepath to upload to HMRC."""
    return str(Path(settings.HMRC_STORAGE_DIRECTORY) / filename)
class Envelope(models.Model):
    """
    Represents a TARIC3 envelope.

    An Envelope contains one or more Transactions, listing changes to be applied
    to the tariff in the sequence defined by the transaction IDs.
    """

    objects: EnvelopeQuerySet = EnvelopeManager.from_queryset(
        EnvelopeQuerySet,
    )()

    envelope_id = EnvelopeId(unique=True)
    xml_file = models.FileField(storage=HMRCStorage, upload_to=to_hmrc,  default='')
    created_date = models.DateTimeField(auto_now_add=True, editable=False, null=True)

    def __repr__(self):
        return f'<Envelope: envelope_id="{self.envelope_id}">'

    class Meta:
        ordering = ("envelope_id",)


class EnvelopeTransaction(models.Model):
    """Applies a sequence to Transactions contained in an Envelope."""

    order = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    envelope = models.ForeignKey(Envelope, on_delete=models.CASCADE)

    class Meta:
        ordering = ("order",)
