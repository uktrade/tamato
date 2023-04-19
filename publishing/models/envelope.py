import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

import boto3
import botocore
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import FileField
from django.db.models import Manager
from django.db.models import Q
from django.db.models import QuerySet
from django.db.transaction import atomic
from lxml import etree

from common.models.mixins import TimestampedMixin
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from publishing.models.packaged_workbasket import PackagedWorkBasket
from publishing.models.state import ProcessingState
from publishing.storages import EnvelopeStorage
from publishing.util import TaricDataAssertionError
from publishing.util import validate_envelope
from taric import validators
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)
# VARIATION_SELECTOR enables emoji presentation
WARNING_SIGN_EMOJI = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"


# Exceptions
class EnvelopeCurrentlyProccessing(Exception):
    pass


class EnvelopeInvalidQueuePosition(Exception):
    pass


class EnvelopeNoTransactions(Exception):
    pass


class MultipleEnvelopesGenerated(Exception):
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
    def deleted(self):
        """Filter in only those Envelope instances that have either a `deleted`
        attribute of `True` or no valid `xml_file` attribute (i.e. None)."""
        return self.filter(
            Q(deleted=True) | Q(xml_file=""),
        )

    def non_deleted(self):
        """Filter in only those Envelope instances that have both a `deleted`
        attribute of `False` and a valid `xml_file` attribute (i.e. not
        None)."""
        return self.filter(
            Q(deleted=False) & ~Q(xml_file=""),
        )

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

    def processed(self):
        return self.filter(
            Q(
                packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
            )
            | Q(
                packagedworkbaskets__processing_state=ProcessingState.FAILED_PROCESSING,
            ),
        )

    def unprocessed(self):
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.AWAITING_PROCESSING,
        )

    def currently_processing(self):
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.CURRENTLY_PROCESSING,
        )

    def all_latest(self):
        return self.filter(
            Q(
                packagedworkbaskets__processing_state=ProcessingState.AWAITING_PROCESSING,
            )
            | Q(
                packagedworkbaskets__processing_state=ProcessingState.CURRENTLY_PROCESSING,
            )
            | Q(
                packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
            ),
        )

    def successfully_processed(self):
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
        )

    def failed_processing(self):
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.FAILED_PROCESSING,
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


def is_delete_marker(s3_object_version):
    """Return True if an object version is a delete marker (i.e. has been
    deleted), False otherwise."""
    try:
        # Use the more efficient head() rather than get().
        s3_object_version.head()
        return False
    except botocore.exceptions.ClientError as e:
        if "x-amz-delete-marker" in e.response["ResponseMetadata"]["HTTPHeaders"]:
            return True
        elif "404" == e.response["Error"]["Code"]:
            # An older version of the key but not a DeleteMarker
            return False
        else:
            return False


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
    xml_file = FileField(
        storage=EnvelopeStorage,
        default="",
    )
    published_to_tariffs_api = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )
    """
    Used to manually set when an envelope has been published to the production
    tariff-api.

    When non-null indicates that an envelope has been published to the tariff-
    api service and when that was done.
    """
    deleted = BooleanField(
        default=False,
        editable=False,
    )
    """Marks an envelope as deleted within contexts where an instance can not be
    immediately deleted from the DB."""

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

    def get_versions(self) -> EnvelopeQuerySet:
        """Return a queryset of all processed Envelopes (all those that have
        been accepted or rejected) that have the same envelope ID as this
        envelope instance."""
        envelope_qs = (
            Envelope.objects.filter(envelope_id=self.envelope_id)
            .non_deleted()
            .processed()
            .order_by("-pk")
        )
        return envelope_qs

    @property
    def xml_file_exists(self) -> bool:
        """Returns True if an S3 object exists for this instance's `xml_file`
        attribute, False otherwise."""
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION_NAME,
        )
        bucket = s3.Bucket(settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME)
        objs = bucket.objects.filter(Prefix=self.xml_file.name, MaxKeys=1)
        return len(list(objs)) > 0

    @property
    def xml_file_name(self):
        return f"DIT{str(self.envelope_id)}.xml"

    @property
    def processing_state_description(self) -> str:
        return self.packagedworkbaskets.last().get_processing_state_display()

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

        # transactions: will be serialized, then added to an envelope for upload.
        workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
        transactions = workbaskets.ordered_transactions()

        if not transactions:
            msg = f"transactions to upload:  {transactions.count()} does not contain any transactions."
            logger.error(msg)
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

            rendered_envelopes = list(
                serializer.split_render_transactions(transactions),
            )
            if len(rendered_envelopes) > 1:
                msg = f"Multiple envelopes generated for workbasket:  {workbasket.pk}."
                logger.error(msg)
                raise MultipleEnvelopesGenerated(msg)

            rendered_envelope = rendered_envelopes[0]
            logger.info(f"rendered_envelope {rendered_envelope}")
            envelope_file = rendered_envelope.output

            # Transaction envelope data XML is valid, ready for upload to s3
            envelope_file.seek(0, os.SEEK_SET)
            try:
                validate_envelope(envelope_file, workbaskets)
            except etree.DocumentInvalid:
                logger.error(f"{envelope_file.name}  is Envelope invalid !")
                raise
            except TaricDataAssertionError:
                # Logged error in validate_envelope
                raise
            else:
                # If valid upload to s3
                total_transactions = len(rendered_envelope.transactions)
                logger.info(
                    f"{envelope_file.name} \N{WHITE HEAVY CHECK MARK}  XML valid.  {total_transactions} transactions, using {envelope_file.tell()} bytes.",
                )

                envelope_file.seek(0, os.SEEK_SET)
                content_file = ContentFile(envelope_file.read())
                self.xml_file = content_file

                envelope_file.seek(0, os.SEEK_SET)

                self.xml_file.save(self.xml_file_name, content_file)

                logger.info("Workbasket saved to CDS S3 bucket")
                logger.debug("Uploaded: %s", self.xml_file_name)

    def __repr__(self):
        return f'<Envelope: envelope_id="{self.envelope_id}">'
