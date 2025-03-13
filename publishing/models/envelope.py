import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

import boto3
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import FileField
from django.db.models import IntegerChoices
from django.db.models import Manager
from django.db.models import PositiveSmallIntegerField
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


class MultipleEnvelopesGenerated(Exception):
    pass


class ValidationState(IntegerChoices):
    """
    Envelope validation states.

    Failure states directly map to the exceptions that may be raised by
    validating an envelope using `publishing.util.validate_envelope()`.
    """

    NOT_VALIDATED = 1, "Not validated"
    """Indeterminate validity state / not yet completely validated."""

    SUCCESSFULLY_VALIDATED = 2, "Successfully validated"
    """Validation has been performed and was Successful."""

    FAILED_DOCUMENT_INVALID = 3, "Document invalid"
    """Failed validation due to etree.DocumentInvalid exception."""

    FAILED_TARIC_DATA_ASSERTION_ERROR = 4, "TARIC data assertion error"
    """Failed validation due to TaricDataAssertionError exception."""

    @classmethod
    def failed_validation_states(cls):
        """Return all states that represent envelope validation failure."""
        return (
            cls.FAILED_DOCUMENT_INVALID,
            cls.FAILED_TARIC_DATA_ASSERTION_ERROR,
        )


class EnvelopeManager(Manager):
    @atomic
    def create(self, packaged_work_basket: PackagedWorkBasket, **kwargs) -> "Envelope":
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
    def deleted(self) -> "EnvelopeQuerySet":
        """Filter in only those Envelope instances that have either a `deleted`
        attribute of `True` or no valid `xml_file` attribute (i.e. None)."""
        return self.filter(
            Q(deleted=True) | Q(xml_file=""),
        )

    def non_deleted(self) -> "EnvelopeQuerySet":
        """Filter in only those Envelope instances that have both a `deleted`
        attribute of `False` and a valid `xml_file` attribute (i.e. not
        None)."""
        return self.filter(
            Q(deleted=False) & ~Q(xml_file=""),
        )

    def successfully_validated(self) -> "EnvelopeQuerySet":
        """Filter in only those Envelope instances against which a successful
        validation check has been performed."""
        return self.filter(
            validation_state=ValidationState.SUCCESSFULLY_VALIDATED,
        )

    def for_year(self, year: Optional[int] = None) -> "EnvelopeQuerySet":
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

    def last_envelope_for_year(self, year=None) -> "Envelope":
        """"""
        return (
            Envelope.objects.for_year(year)
            .filter(
                packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
            )
            .last()
        )

    def processed(self) -> "EnvelopeQuerySet":
        return self.filter(
            Q(
                packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
            )
            | Q(
                packagedworkbaskets__processing_state=ProcessingState.FAILED_PROCESSING,
            ),
        )

    def unprocessed(self) -> "EnvelopeQuerySet":
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.AWAITING_PROCESSING,
        )

    def currently_processing(self) -> "EnvelopeQuerySet":
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.CURRENTLY_PROCESSING,
        )

    def successfully_processed(self) -> "EnvelopeQuerySet":
        return self.filter(
            packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
        )

    def failed_processing(self) -> "EnvelopeQuerySet":
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
    validation_state = PositiveSmallIntegerField(
        choices=ValidationState.choices,
        default=ValidationState.NOT_VALIDATED,
    )
    """Validation state captured from the result of calling
    `publishing.util.validate_envelope()` with the Envelope instance's
    `xml_file` object."""

    @classmethod
    def next_envelope_id(cls) -> str:
        """Provide the next envelope_id for regular publishing, manually
        publishing and publishing in the new year."""
        # last envelope for the current year
        previous_envelope = Envelope.objects.last_envelope_for_year()
        seed_id = settings.HMRC_PACKAGING_SEED_ENVELOPE_ID
        current_year = str(datetime.now().year)[-2:]

        if (previous_envelope is None) and (seed_id[:2] != current_year):
            # First envelope of the year in the format of YYCCCC.
            counter = current_year + "0001"
        else:
            counter = max(
                (int(previous_envelope.envelope_id) + 1) if previous_envelope else 1,
                int(seed_id) + 1,
            )

            if counter > (int(current_year + "0000") + 9999):
                raise ValueError(
                    "Cannot create more than 9999 Envelopes on a single year.",
                )
            counter = str(counter)

        return f"{counter}"

    def delete_envelope(self, **kwargs):
        """Delete function within model to ensure that the file is deleted from
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
            aws_access_key_id=settings.HMRC_PACKAGING_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.HMRC_PACKAGING_S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.HMRC_PACKAGING_S3_REGION_NAME,
        )
        bucket = s3.Bucket(settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME)
        objs = bucket.objects.filter(Prefix=self.xml_file.name, MaxKeys=1)
        return len(list(objs)) > 0

    @property
    def xml_file_name(self) -> str:
        return f"DIT{str(self.envelope_id)}.xml"

    @property
    def processing_state_description(self) -> str:
        """Get the humanised description string of the associated packaged
        workbasket's processing state."""
        return self.packagedworkbaskets.last().get_processing_state_display()

    @property
    def successfully_validated(self) -> bool:
        """Return True if the object's envelope has been successfully validated,
        False otherwise."""
        return self.validation_state == ValidationState.SUCCESSFULLY_VALIDATED

    @atomic
    def upload_envelope(self, workbasket: WorkBasket) -> ValidationState:
        """
        This method performs the following in order:
        - Creates a TARIC3 XML file representation of `workbasket`.
        - Validates the contents of the XML file.
        - If validation fails, then the XML file is not saved (since it is
          invalid).
        - Else, if validation succeeds, then the XML file is saved to S3 and
          associated with `Envelope.xml_file`.

        The method returns the validation state of the XML envelope.
        """

        # transactions: will be serialized, then added to an envelope for upload.
        workbaskets = WorkBasket.objects.filter(pk=workbasket.pk)
        transactions = workbaskets.ordered_transactions()

        # Envelope XML is written to temporary files for validation before
        # anything is created in the database or uploaded to s3.
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

            # Validate the XML envelope.
            envelope_file.seek(0, os.SEEK_SET)
            try:
                validate_envelope(envelope_file, workbaskets)
            except etree.DocumentInvalid:
                logger.error(
                    f"{envelope_file.name} validation failed with "
                    f"DocumentInvalid exception!",
                )
                self.validation_state = ValidationState.FAILED_DOCUMENT_INVALID
                self.save()
                return self.validation_state
            except TaricDataAssertionError:
                # Logged error in validate_envelope
                logger.error(
                    f"{envelope_file.name} validation failed with "
                    f"TaricDataAssertionError exception!",
                )
                self.validation_state = (
                    ValidationState.FAILED_TARIC_DATA_ASSERTION_ERROR
                )
                self.save()
                return self.validation_state

            # Transaction envelope data XML is valid, ready for upload to s3
            self.validation_state = ValidationState.SUCCESSFULLY_VALIDATED
            self.save()

            total_transactions = len(rendered_envelope.transactions)
            logger.info(
                f"{envelope_file.name} {{WHITE HEAVY CHECK MARK}}  XML "
                f"valid. {total_transactions} transactions, using "
                f"{envelope_file.tell()} bytes.",
            )

            envelope_file.seek(0, os.SEEK_SET)
            content_file = ContentFile(envelope_file.read())
            self.xml_file = content_file
            envelope_file.seek(0, os.SEEK_SET)
            self.xml_file.save(self.xml_file_name, content_file)

            logger.info("Workbasket saved to CDS S3 bucket")
            logger.debug("Uploaded: %s", self.xml_file_name)

            return self.validation_state

    def __repr__(self) -> str:
        return f'<Envelope: envelope_id="{self.envelope_id}">'
