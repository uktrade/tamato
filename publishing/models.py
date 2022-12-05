from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.db.models import QuerySet
from django.db.models import TextChoices
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django_fsm import FSMField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from taric.models import Envelope
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


class PackagedWorkBasketInvalidCheckStatus(Exception):
    pass


class PackagedWorkBasketDuplication(Exception):
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
    """Picked off the queue and now being actively processed - now attempting to
    ingest envelope into CDS."""
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

    @classmethod
    def queued_states(cls):
        return (cls.AWAITING_PROCESSING,)

    @classmethod
    def active_states(cls):
        return (cls.CURRENTLY_PROCESSING,)

    @classmethod
    def completed_processing_states(cls):
        return (
            cls.SUCCESSFULLY_PROCESSED,
            cls.FAILED_PROCESSING,
        )


class LoadingReport(TimestampedMixin):
    """Reported associated with an attempt to load (process) a
    PackagedWorkBasket instance."""

    # TODO


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

    def completed_processing(self) -> "PackagedWorkBasketQuerySet":
        """Return all PackagedWorkBasket instances whose processing_state is one
        of the completed processing states."""
        return self.filter(
            processing_state__in=ProcessingState.completed_processing_states(),
        )


class PackagedWorkBasket(TimestampedMixin):
    """
    Encapsulates state and behaviour of a WorkBasket on its journey through the
    packaging process.

    A PackagedWorkBasket must be queued, in priority order, allowing HMRC users
    to pick only the top-most instance when attempting a CDS ingestion. In order
    for a workbasket to be submitted for packaging it must have a complete and
    successful set of rules checks and its status must be APPROVED, indicating
    that it has passed through the review process.
    """

    class Meta:
        ordering = ["position"]

    objects: PackagedWorkBasketQuerySet = PackagedWorkBasketQuerySet.as_manager()

    workbasket = models.ForeignKey(
        WorkBasket,
        on_delete=models.PROTECT,
        editable=False,
    )
    position = models.PositiveSmallIntegerField(
        db_index=True,
        editable=False,
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

    # Creation management.

    @classmethod
    @atomic
    def create(cls, workbasket):
        """Create and save a new instance, associating with workbasket and
        appending the instance to the end (last position) of the package
        processing queue."""

        if workbasket.status in WorkflowStatus.unchecked_statuses():
            raise PackagedWorkBasketInvalidCheckStatus(
                f"Unable to create PackagedWorkBasket from {workbasket} due to "
                f"unchecked status {workbasket.status}",
            )

        packaged_work_baskets = PackagedWorkBasket.objects.filter(
            workbasket=workbasket,
            processing_state__in=(
                ProcessingState.queued_states() + ProcessingState.active_states()
            ),
        )
        if packaged_work_baskets.exists():
            raise PackagedWorkBasketDuplication(
                f"Unable to create PackagedWorkBasket from {workbasket} since "
                "it is already packaged and actively queued - "
                f"{packaged_work_baskets}.",
            )

        max_position = cls.objects.aggregate(
            out=Coalesce(
                Max("position"),
                Value(0),
            ),
        )["out"]
        obj = cls(
            workbasket=workbasket,
            position=max_position + 1,
        )
        return obj.save()

    # processing_state transition management.

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

    # Queue management.

    @atomic
    def pop_top(self):
        """
        Pop the top-most instance, shuffling all remaining queued instances
        (with `state` AWAITING_PROCESSING) up one position.

        Management of the popped instance's `processing_state` is not altered by
        this function and should be managed separately by the caller.
        """
        # TODO:
        return self

    @atomic
    def promote_to_top_position(self):
        """Promote the instance to the top position of the package processing
        queue so that it occupies position 1."""
        # TODO:
        # * Bulk update on position col, set self=1 and decrement those between
        #   position and 1.
        return self

    @atomic
    def promote_position(self):
        """Promote the instance by one position up the package processing
        queue."""
        # TODO:
        # * Check current position and return if already in top position.
        # * Bulk update on position col, swapping self and ahead.
        return self

    @atomic
    def demote_position(self):
        """Demote the instance by one position down the package processing
        queue."""
        # TODO:
        # * Validate that the instance is queued / in the correct state
        #   (UNREVIEWED_AWAITING_PROCESSING).
        # * Check current position and return if already in last position.
        # * Bulk update on position col, swapping self and behind.
        return self
