import logging
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import PROTECT
from django.db.models import SET_NULL
from django.db.models import CharField
from django.db.models import DateField
from django.db.models import DateTimeField
from django.db.models import F
from django.db.models import ForeignKey
from django.db.models import Manager
from django.db.models import Max
from django.db.models import PositiveSmallIntegerField
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import TextField
from django.db.models import URLField
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.utils.timezone import make_aware
from django_fsm import FSMField
from django_fsm import transition

from common.models.mixins import TimestampedMixin
from common.util import TableLock
from notifications.models import EnvelopeAcceptedNotification
from notifications.models import EnvelopeReadyForProcessingNotification
from notifications.models import EnvelopeRejectedNotification
from notifications.models import NotificationLog
from publishing import models as publishing_models
from publishing.models.decorators import save_after
from publishing.models.decorators import skip_notifications_if_disabled
from publishing.models.state import ProcessingState
from publishing.tasks import schedule_create_xml_envelope_file
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

# Decorators


def pop_top_after(func):
    """
    Call pop_top() on an instance.

    This is mainly to allow a state transition to complete before pop_top() is
    called.
    """

    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.pop_top()
        return result

    return inner


def create_envelope_on_completed_processing(func):
    """Decorator used to wrap processing_succeeded and processing_failed
    processing_state transition functions in order to create the next envelope
    when they've completed."""

    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if not PackagedWorkBasket.objects.currently_processing():
            PackagedWorkBasket.create_envelope_for_top()
        return result

    return inner


def create_envelope_on_new_top(func):
    """
    Decorator used to wrap functions that may change the top-most
    PackagedWorkBasket.

    When a when the top-most instance is changed and no other PackagedWorkBasket
    is being processed (i.e. having processing state CURRENTLY_PROCESSING) then
    this decorator will schedule envelope creation for the new top-most
    instance.
    """

    def inner(self, *args, **kwargs):
        if PackagedWorkBasket.objects.currently_processing():
            # Envelopes are only generated when nothing is currently being
            # processed, so just execute the wrapped function and then return.
            return func(self, *args, **kwargs)

        top_before = PackagedWorkBasket.objects.get_top_awaiting()

        result = func(self, *args, **kwargs)

        top_after = PackagedWorkBasket.objects.get_top_awaiting()
        if top_before != top_after:
            # Deletes the envelope created for the previous packaged workbasket
            # Deletes from s3 and the Envelope model, nulls reference in packaged workbasket
            top_before.refresh_from_db()
            if top_before.envelope:
                top_before.envelope.delete_envelope()
                top_before.envelope.save()
                top_before.envelope = None
                top_before.save()
            PackagedWorkBasket.create_envelope_for_top()

        return result

    return inner


# Exceptions
class PackagedWorkBasketDuplication(Exception):
    pass


class PackagedWorkBasketInvalidCheckStatus(Exception):
    pass


class PackagedWorkBasketInvalidQueueOperation(Exception):
    pass


class PackagedWorkBasketManager(Manager):
    @atomic
    @TableLock.acquire_lock("publishing.PackagedWorkBasket", lock=TableLock.EXCLUSIVE)
    def create(self, workbasket: WorkBasket, **kwargs):
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

        new_obj = super().create(workbasket=workbasket, position=position, **kwargs)

        # If this instance is created at queue position 1 and no other
        # PackagedWorkBasket is being processed then schedule envelope creation.
        # See `publishing.tasks.create_xml_envelope_file()` for details.
        if (
            not PackagedWorkBasket.objects.currently_processing()
            and new_obj == PackagedWorkBasket.objects.get_top_awaiting()
        ):
            schedule_create_xml_envelope_file(
                packaged_work_basket=new_obj,
                notify_when_done=True,
                seconds_delay=1,
            )

        return new_obj


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
        """Return the maxium position value of any PackagedWorkBasket
        instance."""
        return PackagedWorkBasket.objects.aggregate(out=Max("position"))["out"]

    def get_top_awaiting(self):
        """Return the top-most (position 1) PackagedWorkBasket instance with
        processing_state ProcessingState.AWAITING_PROCESSING, else None if there
        there are no such instances."""
        top = self.filter(
            processing_state=ProcessingState.AWAITING_PROCESSING,
            position=1,
        )
        return top.first() if top else None

    def get_next_unpublished_to_api(self) -> "PackagedWorkBasket":
        """Return the next successfully processed packaged workbasket (ordered
        by envelope__envelope_id) that does not have a published envelope and
        crown_dependencies_envelope."""
        return self.get_unpublished_to_api().first()

    def get_unpublished_to_api(self) -> "PackagedWorkBasketQuerySet":
        """Return all successfully processed packaged workbaskets (ordered by
        envelope__envelope_id) that do not have a published envelope and
        crown_dependencies_envelope."""
        unpublished = self.filter(
            Q(
                processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
                crown_dependencies_envelope__isnull=True,
                # Filters out older envelopes that do not have a crown_dependencies_envelope
                envelope__published_to_tariffs_api__isnull=True,
            ),
        ).order_by("envelope__envelope_id")
        return unpublished

    def last_unpublished_envelope_id(self) -> "publishing_models.EnvelopeId":
        """Join PackagedWorkBasket with Envelope and CrownDependenciesEnvelope
        model selecting objects Where an Envelope model exists and the
        published_to_tariffs_api field is not null Or Where a
        CrownDependenciesEnvelope is not null Then select the max value for ther
        envelope_id field in the Envelope instance."""

        return (
            self.select_related(
                "envelope",
                "crown_dependencies_envelope",
            )
            .filter(
                Q(
                    envelope__id__isnull=False,
                    envelope__published_to_tariffs_api__isnull=False,
                )
                | Q(crown_dependencies_envelope__id__isnull=False),
            )
            .aggregate(
                Max("envelope__envelope_id"),
            )["envelope__envelope_id__max"]
        )


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
        verbose_name_plural = "packaged workbaskets"
        permissions = [
            ("manage_packaging_queue", "Can manage the packaging queue"),
            ("consume_from_packaging_queue", "Can consume from the packaging queue"),
        ]

    objects: PackagedWorkBasketQuerySet = PackagedWorkBasketManager.from_queryset(
        PackagedWorkBasketQuerySet,
    )()

    workbasket = ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=PROTECT,
        editable=False,
    )
    position = PositiveSmallIntegerField(
        db_index=True,
        editable=False,
    )
    """
    Position 1 is the top position, ready for processing.

    An instance that is being processed or has been processed has its position
    value set to 0.
    """
    envelope = ForeignKey(
        "publishing.Envelope",
        null=True,
        on_delete=SET_NULL,
        editable=False,
        related_name="packagedworkbaskets",
    )
    crown_dependencies_envelope = ForeignKey(
        "publishing.CrownDependenciesEnvelope",
        null=True,
        on_delete=SET_NULL,
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
    processing_started_at = DateTimeField(
        null=True,
        blank=True,
        default=None,
    )
    """The date and time at which processing_state transitioned to
    CURRENTLY_PROCESSING."""
    theme = CharField(
        max_length=255,
    )
    description = TextField(
        blank=True,
    )
    eif = DateField(
        null=True,
        blank=True,
        help_text="For Example, 27 3 2008",
    )
    """
    The enter into force date determines when changes should go live in CDS.

    A file will need to be ingested by CDS on the day before this. If left,
    blank CDS will ingest the file immediately.
    """
    embargo = CharField(
        blank=True,
        null=True,
        max_length=255,
    )
    """The date until which CDS prevents envelope from being displayed after
    ingestion."""
    jira_url = URLField(
        help_text="Insert Tops Jira ticket link",
    )
    """URL linking the packaged workbasket with a ticket on the Tariff
    Operations (TOPS) project's Jira board."""
    create_envelope_task_id = CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )
    """
    ID of Celery task used to generate this instance's associated envelope.

    Its necessary to set null=True (unusually for CharField) in order to support
    the unique=True attribute.
    """

    @property
    def has_envelope(self):
        """Conditional check for if the packaged workbasket has an evnvelope."""
        return self.envelope and self.envelope.xml_file and not self.envelope.deleted

    @classmethod
    def create_envelope_for_top(cls):
        """Schedule the envelope generation process for the top-most (position
        1) instance."""
        top = cls.objects.get_top_awaiting()
        if top:
            schedule_create_xml_envelope_file(
                packaged_work_basket=top,
                notify_when_done=True,
                seconds_delay=1,
            )
        else:
            logger.info(
                "Attempted to schedule top for envelope creation, but no top "
                "exists.",
            )

    def next_expected_to_api(self) -> bool:
        """
        Checks if previous envelope in sequence has been published to the API.

        This check will check if the previous packaged workbasket has a
        CrownDependenciesEnvelope OR has published_to_tariffs_api set in the
        Envelope model. Will return True if the previous_id comes back as None
        (this means the envelope is the first to be published to the API)
        """

        previous_id = PackagedWorkBasket.objects.last_unpublished_envelope_id()
        if self.envelope.envelope_id[2:] == settings.HMRC_PACKAGING_SEED_ENVELOPE_ID:
            year = int(self.envelope.envelope_id[:2])
            last_envelope = publishing_models.Envelope.objects.for_year(
                year=year - 1,
            ).last()
            # uses None if first envelope (no previous ones)
            expected_previous_id = last_envelope.envelope_id if last_envelope else None
        else:
            expected_previous_id = str(
                int(self.envelope.envelope_id) - 1,
            )
        if previous_id and previous_id != expected_previous_id:
            return False
        return True

    # processing_state transition management.

    def begin_processing_condition_at_position_1(self) -> bool:
        """Django FSM condition: Instance must be at position 1 in order to
        complete the begin_processing transition to CURRENTLY_PROCESSING."""

        self.refresh_from_db(fields=["position"])
        return self.position == 1

    def begin_processing_condition_no_instances_currently_processing(self) -> bool:
        """Django FSM condition: No other instance is currently being processed
        in order to complete the begin_processing and transition this instance
        to CURRENTLY_PROCESSING."""

        return not PackagedWorkBasket.objects.currently_processing()

    @atomic
    @pop_top_after
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
        instance = PackagedWorkBasket.objects.select_for_update(nowait=True).get(
            pk=self.pk,
        )
        instance.processing_started_at = make_aware(datetime.now())
        instance.save()

    @create_envelope_on_completed_processing
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
        self.workbasket.cds_confirmed()
        self.workbasket.save()
        self.notify_processing_succeeded()

    @create_envelope_on_completed_processing
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
        self.workbasket.cds_error()
        self.workbasket.save()
        self.notify_processing_failed()

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
        self.workbasket.dequeue()
        self.workbasket.save()

    @atomic
    def refresh_from_db(self, using=None, fields=None):
        """Reload instance from database but avoid writing to
        self.processing_state directly in order to avoid the exception
        'AttributeError: Direct processing_state modification is not
        allowed.'."""
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

    @skip_notifications_if_disabled
    def notify_ready_for_processing(self):
        """
        Notify users that an envelope is ready to download and process.

        This requires that the envelope has been generated and saved and is
        therefore normally called when the process for doing that has completed
        (see `publishing.tasks.create_xml_envelope_file()`).
        """
        notification = EnvelopeReadyForProcessingNotification(
            notified_object_pk=self.pk,
        )
        notification.save()
        notification.schedule_send_emails()

    @skip_notifications_if_disabled
    def notify_processing_succeeded(self):
        """Notify users that envelope processing has succeeded (i.e. the
        associated envelope was correctly ingested into HMRC systems)."""
        notification = EnvelopeAcceptedNotification(
            notified_object_pk=self.pk,
        )
        notification.save()
        notification.schedule_send_emails()

    @skip_notifications_if_disabled
    def notify_processing_failed(self):
        """Notify users that envelope processing has failed (i.e. HMRC systems
        rejected this instance's associated envelope file)."""
        notification = EnvelopeRejectedNotification(
            notified_object_pk=self.pk,
        )
        notification.save()
        notification.schedule_send_emails()

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
    @create_envelope_on_new_top
    def pop_top(self) -> "PackagedWorkBasket":
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

        PackagedWorkBasket.objects.select_for_update(nowait=True).filter(
            position__gt=0,
        ).update(
            position=F("position") - 1,
        )
        self.refresh_from_db()

        return self

    @atomic
    @create_envelope_on_new_top
    def remove_from_queue(self) -> "PackagedWorkBasket":
        """
        Remove instance from the queue, shuffling all successive queued
        instances (with `state` AWAITING_PROCESSING) up one position.

        Management of the queued instance's `processing_state` is not altered by
        this function and should be managed separately by the caller.
        """

        PackagedWorkBasket.objects.select_for_update(nowait=True).get(pk=self.pk)
        self.refresh_from_db()

        if self.position == 0:
            raise PackagedWorkBasketInvalidQueueOperation(
                "Unable to remove instance with a position value of 0 from "
                "queue because 0 indicates that it is not a queue member.",
            )

        current_position = self.position
        self.position = 0
        self.save()

        PackagedWorkBasket.objects.select_for_update(nowait=True).filter(
            position__gt=current_position,
        ).update(
            position=F("position") - 1,
        )
        self.refresh_from_db()

        return self

    @atomic
    @create_envelope_on_new_top
    def promote_to_top_position(self) -> "PackagedWorkBasket":
        """Promote the instance to the top position of the package processing
        queue so that it occupies position 1."""

        PackagedWorkBasket.objects.select_for_update(nowait=True).get(pk=self.pk)
        self.refresh_from_db()

        if self.position <= 1:
            return self

        position = self.position

        PackagedWorkBasket.objects.select_for_update(nowait=True).filter(
            Q(position__gte=1) & Q(position__lt=position),
        ).update(position=F("position") + 1)

        self.position = 1
        self.save()
        self.refresh_from_db()

        return self

    @atomic
    @create_envelope_on_new_top
    def promote_position(self) -> "PackagedWorkBasket":
        """Promote the instance by one position up the package processing
        queue."""

        PackagedWorkBasket.objects.select_for_update(nowait=True).get(pk=self.pk)
        self.refresh_from_db()

        if self.position <= 1:
            return self

        obj_to_swap = PackagedWorkBasket.objects.select_for_update(nowait=True).get(
            position=self.position - 1,
        )
        obj_to_swap.position += 1
        self.position -= 1
        PackagedWorkBasket.objects.bulk_update(
            [self, obj_to_swap],
            ["position"],
        )
        self.refresh_from_db()

        return self

    @atomic
    @create_envelope_on_new_top
    def demote_position(self) -> "PackagedWorkBasket":
        """Demote the instance by one position down the package processing
        queue."""

        PackagedWorkBasket.objects.select_for_update(nowait=True).get(pk=self.pk)
        self.refresh_from_db()

        if self.position in {0, PackagedWorkBasket.objects.max_position()}:
            return self

        obj_to_swap = PackagedWorkBasket.objects.select_for_update(nowait=True).get(
            position=self.position + 1,
        )
        obj_to_swap.position -= 1
        self.position += 1
        PackagedWorkBasket.objects.bulk_update(
            [self, obj_to_swap],
            ["position"],
        )
        self.refresh_from_db()

        return self
