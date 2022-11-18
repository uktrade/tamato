from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import TextChoices
from django_fsm import FSMField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from taric.models import Envelope
from workbaskets.models import WorkBasket


class ProcessingState(TextChoices):
    """Processing states of PackagedWorkBasket instances."""

    # Queued up and awaiting processing.
    AWAITING_PROCESSING = (
        "AWAITING_PROCESSING ",
        "Awaiting processing",
    )
    # Picked off the queue and now being actively processed - now attempting to ingest envelope into CDS.
    CURRENTLY_PROCESSING = (
        "CURRENTLY_PROCESSING ",
        "Currently processing",
    )
    # Processing now completed with a successful outcome - envelope ingested into CDS.
    SUCCESSFULLY_PROCESSED = (
        "SUCCESSFULLY_PROCESSED ",
        "Successfully processed",
    )
    # Processing now completed with a failure outcome - CDS rejected the envelope.
    FAILED_PROCESSING = (
        "FAILED_PROCESSING ",
        "Failed processing",
    )


class LoadingReport(TimestampedMixin):
    """Reported associated with an attempt to load (process) a
    PackagedWorkBasket instance."""


class PackagedWorkBasket(TimestampedMixin):
    """
    Encapsulates state and behaviour of a WorkBasket passing through the
    packaging process.

    A PackagedWorkBasket must be queued, allowing HMRC users to pick the top-
    most instance only to attempt CDS ingestion. The packaging process handles
    CDS ingestion success and failure cases.
    """

    workbasket = models.ForeignKey(
        WorkBasket,
        on_delete=models.PROTECT,
        editable=False,
    )
    position = models.SmallIntegerField(
        db_index=True,
        editable=False,
        validators=[
            MinValueValidator(0),
        ],
    )
    """Position 1 is the top position, ready for processing. An instance that
    is being processed or has been processed has its position value set to 0.
    """
    envelope = models.ForeignKey(
        Envelope,
        null=True,
        on_delete=models.PROTECT,
        editable=False,
    )
    processing_state = FSMField(
        default=ProcessingState.AWAITING_PROCESSING,
        choices=ProcessingState.choices,
        db_index=True,
        protected=True,
        editable=False,
    )
    loading_report = models.ForeignKey(
        LoadingReport,
        null=True,
        on_delete=models.PROTECT,
        editable=False,
    )
    """The report file associated with an attempt (either successful or failed)
    to process / load the associated workbasket's envelope file.
    """

    # position_state transition management.

    @transition(
        field=processing_state,
        source=ProcessingState.AWAITING_PROCESSING,
        target=ProcessingState.CURRENTLY_PROCESSING,
        custom={"label": "Begin processing"},
    )
    def begin_processing(self):
        """Start processing a PackagedWorkBasket."""
        # TODO:
        # * Prevent processing anything other the instance in the top position,
        #   1.
        # * Guard against attempts to process more than one instance at any
        #   one time. This avoids an otherwise intractable CDS envelope
        #   sequencing issue that results from a contiguous envelope numbering
        #   requirement, while also supporting envelope ingestion failure since
        #   their envelope IDs become invalid and must be recycled.

    @transition(
        field=processing_state,
        source=ProcessingState.CURRENTLY_PROCESSING,
        target=ProcessingState.FAILED_PROCESSING,
        custom={"label": "Processing succeeded"},
    )
    def processing_succeeded(self):
        """Processing completed with a successful outcome."""

    @transition(
        field=processing_state,
        source=ProcessingState.CURRENTLY_PROCESSING,
        target=ProcessingState.SUCCESSFULLY_PROCESSED,
        custom={"label": "Processing failed"},
    )
    def processing_failed(self):
        """Processing completed with a failed outcome."""

    # Creation management.

    @classmethod
    def create(cls):
        """Create a new instance, appending it to the end (last position) of the
        package processing queue."""
        # TODO:
        # * Assign self.position to MAX(position) + 1.
        return cls.objects.create()

    # Queue positioning.

    def promote_to_top(self):
        """Promote the instance to the top position of the package processing
        queue."""
        # TODO:
        # * Bulk update on position col, set self=1 and decrement those between
        #   position and 1.
        return self

    def promote_position(self):
        """Promote the instance by one position up the package processing
        queue."""
        # TODO:
        # * Check current position and return if already in top position.
        # * Bulk update on position col, swapping self and ahead.
        return self

    def demote_position(self):
        """Demote the instance by one position down the package processing
        queue."""
        # TODO:
        # * Check current position and return if already in last position.
        # * Bulk update on position col, swapping self and behind.
        return self
