import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import F
from django.db.models import Max
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import TextChoices
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django_fsm import FSMField
from django_fsm import transition
from lxml import etree

from common.models.mixins import TimestampedMixin
from common.serializers import validate_envelope
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.util import dit_file_generator
from notifications.models import NotificationLog
from publishing.storages import EnvelopeStorage
from taric import validators
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class OperationalStatusQuerySet(QuerySet):
    def current_status(self):
        return self.order_by("pk").last()


class QueueState(TextChoices):
    PAUSED = ("PAUSED", "Envelope processing is paused")
    UNPAUSED = ("UNPAUSED", "Envelope processing is unpaused and may proceed")


class OperationalStatus(models.Model):
    """
    Operational status of the packaging system.

    The packaging queue's state is of primary concern here: either unpaused,
    which allows processing the next available workbasket, or paused, which
    blocks the begin_processing transition of the next available queued
    workbasket until the system is unpaused.
    """

    class Meta:
        ordering = ["pk"]
        verbose_name_plural = "operational statuses"

    objects = OperationalStatusQuerySet.as_manager()

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
    )
    """If a new instance is created as a result of direct user action (for
    instance pausing or unpausing the packaging queue) then `created_by` should
    be associated with that user."""
    queue_state = models.CharField(
        max_length=8,
        default=QueueState.PAUSED,
        choices=QueueState.choices,
        editable=False,
    )

    @classmethod
    def pause_queue(cls, user: settings.AUTH_USER_MODEL) -> "OperationalStatus":
        """
        Transition the workbasket queue into a paused state (if it is not
        already paused) by creating a new `OperationalStatus` and returning it
        to the caller.

        If the queue is already paused, then do nothing and return None.
        """
        if cls.is_queue_paused():
            return None
        return OperationalStatus.objects.create(
            queue_state=QueueState.PAUSED,
            created_by=user,
        )

    @classmethod
    def unpause_queue(cls, user: settings.AUTH_USER_MODEL) -> "OperationalStatus":
        """
        Transition the workbasket queue into an unpaused state (if it is not
        already unpaused) by creating a new `OperationalStatus` and returning it
        to the caller.

        If the queue is already unpaused, then do nothing and return None.
        """
        if not cls.is_queue_paused():
            return None
        return OperationalStatus.objects.create(
            queue_state=QueueState.UNPAUSED,
            created_by=user,
        )

    @classmethod
    def is_queue_paused(cls) -> bool:
        """Returns True if the workbasket queue is paused, False otherwise."""
        current_status = cls.objects.current_status()
        if not current_status or current_status.queue_state == QueueState.PAUSED:
            return True
        else:
            return False


class PackagedWorkBasketDuplication(Exception):
    pass


class PackagedWorkBasketInvalidCheckStatus(Exception):
    pass


class PackagedWorkBasketInvalidQueueOperation(Exception):
    pass


class EnvelopeCurrentlyProccessing(Exception):
    pass


class EnvelopeInvalidQueuePosition(Exception):
    pass


class WorkBasketNoTransactions(Exception):
    pass


class ProcessingState(TextChoices):
    """Processing states of PackagedWorkBasket instances."""

    AWAITING_PROCESSING = (
        "AWAITING_PROCESSING",
        "Reviewed and awaiting processing",
    )
    """Queued up and awaiting processing."""
    CURRENTLY_PROCESSING = (
        "CURRENTLY_PROCESSING",
        "Currently processing",
    )
    """Picked off the queue and now currently being processed - now attempting
    to ingest envelope into CDS."""
    SUCCESSFULLY_PROCESSED = (
        "SUCCESSFULLY_PROCESSED",
        "Successfully processed",
    )
    """Processing now completed with a successful outcome - envelope ingested
    into CDS."""
    FAILED_PROCESSING = (
        "FAILED_PROCESSING",
        "Failed processing",
    )
    """Processing now completed with a failure outcome - CDS rejected the
    envelope."""
    ABANDONED = (
        "ABANDONED",
        "Abandoned",
    )
    """Processing has been abandoned."""

    @classmethod
    def queued_states(cls):
        """Returns all states that represent a queued  instance, including those
        that are being processed."""
        return (cls.AWAITING_PROCESSING, cls.CURRENTLY_PROCESSING)

    @classmethod
    def completed_processing_states(cls):
        return (
            cls.SUCCESSFULLY_PROCESSED,
            cls.FAILED_PROCESSING,
        )


class EnvelopeManager(models.Manager):
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
    def envelopes_by_year(self, year: Optional[int] = None):
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


class Envelope(models.Model):
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
    xml_file = models.FileField(storage=EnvelopeStorage, default="")
    created_date = models.DateTimeField(auto_now_add=True, editable=False, null=True)

    @classmethod
    def next_envelope_id(cls):
        """Get packaged workbaskets where proc state SUCCESS."""
        envelope = (
            Envelope.objects.envelopes_by_year()
            .filter(
                packagedworkbaskets__processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
            )
            .last()
        )

        if envelope is None:
            # First envelope of the year.
            now = datetime.today()
            counter = 1
        else:
            year = int(envelope.envelope_id[:2])
            counter = int(envelope.envelope_id[2:]) + 1

            if counter > 9999:
                raise ValueError(
                    "Cannot create more than 9999 Envelopes on a single year.",
                )

            now = datetime(year, 1, 1)

        return f"{now:%y}{counter:04d}"

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
            raise WorkBasketNoTransactions(msg)

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
                max_envelope_size=settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE,
            )

            rendered_envelope = list(
                serializer.split_render_transactions(transactions),
            )[0]
            logger.info(f"rendered_envelope {rendered_envelope}")
            envelope_file = rendered_envelope.output
            if not rendered_envelope.transactions:
                msg = f"{envelope_file.name}  is empty !"
                logger.error(msg)
                raise WorkBasketNoTransactions(msg)
            # Transaction envelope data XML is valid, ready for upload to s3
            else:
                envelope_file.seek(0, os.SEEK_SET)
                try:
                    validate_envelope(envelope_file)
                except etree.DocumentInvalid:
                    logger.error(f"{envelope_file.name}  is Envelope invalid !")
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


class LoadingReport(TimestampedMixin):
    """Reported associated with an attempt to load (process) a
    PackagedWorkBasket instance."""

    # TODO Change report_file to correct field for / s3 object reference.
    report_file = models.FileField(
        blank=True,
        null=True,
    )
    comment = models.TextField(
        blank=True,
        max_length=200,
    )


def save_after(func):
    @atomic
    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save()
        return result

    return inner


class PackagedWorkBasketManager(models.Manager):
    @atomic
    def create(self, workbasket, **kwargs):
        """Create a new instance, associating with workbasket."""

        if workbasket.status in WorkflowStatus.unchecked_statuses():
            raise PackagedWorkBasketInvalidCheckStatus(
                "Unable to create PackagedWorkBasket from WorkBasket instance "
                f"({workbasket}) due to unchecked {workbasket.status} status.",
            )

        packaged_work_baskets = PackagedWorkBasket.objects.all_queued().filter(
            workbasket=workbasket,
        )
        if packaged_work_baskets.exists():
            raise PackagedWorkBasketDuplication(
                f"Unable to create PackagedWorkBasket from {workbasket} since "
                "it is already packaged and actively queued - "
                f"{packaged_work_baskets}.",
            )

        position = (
            PackagedWorkBasket.objects.aggregate(
                out=Coalesce(
                    Max("position"),
                    Value(0),
                ),
            )["out"]
            + 1
        )

        return super().create(workbasket=workbasket, position=position, **kwargs)


class PackagedWorkBasketQuerySet(QuerySet):
    def awaiting_processing(self) -> "PackagedWorkBasketQuerySet":
        """Return all PackagedWorkBasket instances whose processing_state is set
        to AWAITING_PROCESSING."""
        return self.filter(processing_state=ProcessingState.AWAITING_PROCESSING)

    def currently_processing(self) -> "PackagedWorkBasket":
        """
        Returns a single PackagedWorkBasket instance if one currently has a
        processing_state of CURRENTLY_PROCESSING.

        If no instance has a processing_state of CURRENTLY_PROCESSING, then None
        is returned.
        """
        try:
            return self.get(
                processing_state=ProcessingState.CURRENTLY_PROCESSING,
            )
        except ObjectDoesNotExist:
            return None

    def all_queued(self) -> "PackagedWorkBasketQuerySet":
        """Return all PackagedWorkBasket instances whose processing_state is one
        of the actively queued / non-completed states."""
        return self.filter(
            processing_state__in=ProcessingState.queued_states(),
        )

    def completed_processing(self) -> "PackagedWorkBasketQuerySet":
        """Return all PackagedWorkBasket instances whose processing_state is one
        of the completed processing states."""
        return self.filter(
            processing_state__in=ProcessingState.completed_processing_states(),
        )

    def max_position(self) -> int:
        return PackagedWorkBasket.objects.aggregate(out=Max("position"))["out"]


class PackagedWorkBasket(TimestampedMixin):
    """
    Encapsulates state and behaviour of a WorkBasket on its journey through the
    packaging process.

    A PackagedWorkBasket must be queued, in priority order, allowing HMRC users
    to pick only the top-most instance when attempting a CDS ingestion. In order
    for a workbasket to be submitted for packaging it must have a complete and
    successful set of rules checks and its status must be QUEUED, indicating
    that it has passed through the review process.
    """

    class Meta:
        ordering = ["position"]

    objects: PackagedWorkBasketQuerySet = PackagedWorkBasketManager.from_queryset(
        PackagedWorkBasketQuerySet,
    )()

    workbasket = models.ForeignKey(
        WorkBasket,
        on_delete=models.PROTECT,
        editable=False,
    )
    position = models.PositiveSmallIntegerField(
        db_index=True,
        editable=False,
    )
    """
    Position 1 is the top position, ready for processing.

    An instance that is being processed or has been processed has its position
    value set to 0.
    """
    envelope = models.ForeignKey(
        Envelope,
        null=True,
        on_delete=models.PROTECT,
        editable=False,
        related_name="packagedworkbaskets",
    )
    processing_state = FSMField(
        default=ProcessingState.AWAITING_PROCESSING,
        choices=ProcessingState.choices,
        db_index=True,
        protected=True,
        editable=False,
    )
    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
    )
    """The date and time at which processing_state transitioned to
    CURRENTLY_PROCESSING."""
    loading_report = models.ForeignKey(
        LoadingReport,
        null=True,
        on_delete=models.PROTECT,
        editable=False,
    )
    """The report file associated with an attempt (either successful or failed)
    to process / load the associated workbasket's envelope file."""
    theme = models.CharField(
        max_length=255,
    )
    description = models.TextField(
        blank=True,
    )
    eif = models.DateField(
        null=True,
        blank=True,
        help_text="For Example, 27 3 2008",
    )
    """
    The enter into force date determines when changes should go live in CDS.

    A file will need to be ingested by CDS on the day before this. If left,
    blank CDS will ingest the file immediately.
    """
    embargo = models.CharField(
        blank=True,
        null=True,
        max_length=255,
    )
    """The date until which CDS prevents envelope from being displayed after
    ingestion."""
    jira_url = models.URLField(
        help_text="Insert Tops Jira ticket link",
    )
    """URL linking the packaged workbasket with a ticket on the Tariff
    Operations (TOPS) project's Jira board."""

    # processing_state transition management.

    def begin_processing_condition_at_position_1(self):
        """Django FSM condition: Instance must be at position 1 in order to
        complete the begin_processing transition to CURRENTLY_PROCESSING."""

        return self.position == 1

    def begin_processing_condition_no_instances_currently_processing(self):
        """Django FSM condition: No other instance is currently being processed
        in order to complete the begin_processing and transition this instance
        to CURRENTLY_PROCESSING."""

        return not PackagedWorkBasket.objects.currently_processing()

    @save_after
    @transition(
        field=processing_state,
        source=ProcessingState.AWAITING_PROCESSING,
        target=ProcessingState.CURRENTLY_PROCESSING,
        conditions=[
            begin_processing_condition_at_position_1,
            begin_processing_condition_no_instances_currently_processing,
        ],
        custom={"label": "Begin processing"},
    )
    def begin_processing(self):
        """
        Start processing a PackagedWorkBasket.

        Only a single instance may have its `processing_state` set to
        CURRENTLY_PROCESSING. This is to avoid an otherwise intractable CDS
        envelope sequencing issue that results from a CDS contiguous envelope
        numbering requirement - CDS failed envelope IDs must be recycled and
        therefore CDS envelope processing must complete to establish the correct
        next envelope ID.

        A successful transition also sets the instance's position to 0.

        Because transitioning processing_state can update the position of
        multiple instances it's necessary for this method to perform a save()
        operation upon successful transitions.
        """

        self.processing_started_at = datetime.now()
        self.save()
        self.pop_top()

    @save_after
    @transition(
        field=processing_state,
        source=ProcessingState.CURRENTLY_PROCESSING,
        target=ProcessingState.SUCCESSFULLY_PROCESSED,
        custom={"label": "Processing succeeded"},
    )
    def processing_succeeded(self):
        """
        Processing completed with a successful outcome.

        Because transitioning processing_state can update the position of
        multiple instances it's necessary for this method to perform a save()
        operation upon successful transitions.
        """

    @save_after
    @transition(
        field=processing_state,
        source=ProcessingState.CURRENTLY_PROCESSING,
        target=ProcessingState.FAILED_PROCESSING,
        custom={"label": "Processing failed"},
    )
    def processing_failed(self):
        """
        Processing completed with a failed outcome.

        Because transitioning processing_state can update the position of
        multiple instances it's necessary for this method to perform a save()
        operation upon successful transitions.
        """

    @save_after
    @transition(
        field=processing_state,
        source=ProcessingState.AWAITING_PROCESSING,
        target=ProcessingState.ABANDONED,
        custom={"label": "Abandon"},
    )
    def abandon(self):
        """
        Abandon an instance before any processing attempt has been made.

        Because transitioning processing_state can update the position of
        multiple instances it's necessary for this method to perform a save()
        operation upon successful transitions.
        """

        self.remove_from_queue()
        # TODO:
        # Transition self.workbasket.status from QUEUED to EDITING by calling
        # self.workbasket.dequeue() once the transition is implemented.
        # self.workbasket.dequeue()

    @atomic
    def refresh_from_db(self, using=None, fields=None):
        """Reload instance from database but avoid writing to
        self.processing_state directly in order to avoid the exception
        'AttributeError: Direct processing_state modification is not allowed.'
        """
        if fields is None:
            refresh_state = True
            fields = [f.name for f in self._meta.concrete_fields]
        else:
            refresh_state = "processing_state" in fields

        fields_without_state = [f for f in fields if f != "processing_state"]

        super().refresh_from_db(using=using, fields=fields_without_state)

        if refresh_state:
            new_state = (
                type(self)
                .objects.only("processing_state")
                .get(pk=self.pk)
                .processing_state
            )
            self._meta.get_field("processing_state").set_state(self, new_state)

    # Notification management.
    """
    Sending "Ready to download" email notifications
    -
    PackagedWorkBasket.notify_ready_for_processing(self)
    --

    When an instance first arrives at position 1, and no other instance has
    PackagedWorkBasket.state == ProcessingState.CURRENTLY_PROCESSING, then
    call notify_ready_for_processing() with the instance as a parameter.

    When an instance has its PackagedWorkBasket.state transitioned to either
    SUCCESSFULLY_PROCESSED or FAILED_PROCESSING, and there are instances
    with PackagedWorkBasket.state == ProcessingState.AWAITING_PROCESSING,
    then call ready_for_processing() with the instances as a parameter.


    Sending "Ingestion succeeded" and "Ingestion failed" notifications
    -
    PackagedWorkBasket.notify_processing_succeeded(self)
    PackagedWorkBasket.notify_processing_failed(self)
    --

    The functions processing_succeeded() and processing_failed() map to these
    two cases and are called by the state transition methods
    PackagedWorkBasket.notify_processing_succeeded() and
    PackagedWorkBasket.notify_processing_failed(), respectively.
    """

    def notify_ready_for_processing(self):
        """TODO."""

    def notify_processing_succeeded(self):
        """TODO."""

    def notify_processing_failed(self):
        """TODO."""

    @property
    def cds_notified_notification_log(self) -> NotificationLog:
        """
        NotificationLog instance created when HMRC are notified of an instance's
        envelope being ready for processing by CDS.

        None if there is no NotificationLog instance associated with this
        PackagedWorkBasket instance.
        """
        # TODO: Apply correct lookup when .packaged_work_basket is available.
        # return NotificationLog.objects.filter(packaged_work_basket=self).last()
        return NotificationLog.objects.last() if self.position == 1 else None

    # Queue management.

    @atomic
    def pop_top(self):
        """
        Pop the top-most instance, shuffling all remaining queued instances
        (with `state` AWAITING_PROCESSING) up one position.

        Management of the popped instance's `processing_state` is not altered by
        this function and should be managed separately by the caller.
        """

        if self.position != 1:
            raise PackagedWorkBasketInvalidQueueOperation(
                "Unable to pop instance at position {self.position} in queue "
                "because it is not at position 1.",
            )

        PackagedWorkBasket.objects.filter(position__gt=0).update(
            position=F("position") - 1,
        )
        self.refresh_from_db()

        return self

    @atomic
    def remove_from_queue(self):
        """
        Remove instance from the queue, shuffling all successive queued
        instances (with `state` AWAITING_PROCESSING) up one position.

        Management of the queued instance's `processing_state` is not altered by
        this function and should be managed separately by the caller.
        """

        if self.position == 0:
            raise PackagedWorkBasketInvalidQueueOperation(
                "Unable to remove instance with a position value of 0 from "
                "queue because 0 indicates that it is not a queue member.",
            )

        current_position = self.position
        self.position = 0
        self.save()

        PackagedWorkBasket.objects.filter(position__gt=current_position).update(
            position=F("position") - 1,
        )
        self.refresh_from_db()

        return self

    @atomic
    def promote_to_top_position(self):
        """Promote the instance to the top position of the package processing
        queue so that it occupies position 1."""

        if self.position == 1:
            return self

        position = self.position

        PackagedWorkBasket.objects.filter(
            Q(position__gte=1) & Q(position__lt=position),
        ).update(position=F("position") + 1)

        self.position = 1
        self.save()

        return self

    @atomic
    def promote_position(self):
        """Promote the instance by one position up the package processing
        queue."""

        if self.position == 1:
            return

        obj_to_swap = PackagedWorkBasket.objects.get(position=self.position - 1)
        obj_to_swap.position += 1
        self.position -= 1
        PackagedWorkBasket.objects.bulk_update(
            [self, obj_to_swap],
            ["position"],
        )
        self.refresh_from_db()

        return self

    @atomic
    def demote_position(self):
        """Demote the instance by one position down the package processing
        queue."""

        if self.position == PackagedWorkBasket.objects.max_position():
            return

        obj_to_swap = PackagedWorkBasket.objects.get(position=self.position + 1)
        obj_to_swap.position -= 1
        self.position += 1
        PackagedWorkBasket.objects.bulk_update(
            [self, obj_to_swap],
            ["position"],
        )
        self.refresh_from_db()

        return self
