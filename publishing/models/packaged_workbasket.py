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
from django.urls import reverse
from django_fsm import FSMField
from django_fsm import transition
from notifications_python_client import prepare_upload

from common.models.mixins import TimestampedMixin
from notifications.models import NotificationLog
from notifications.tasks import send_emails
from publishing.models.exceptions import PackagedWorkBasketDuplication
from publishing.models.exceptions import PackagedWorkBasketInvalidCheckStatus
from publishing.models.exceptions import PackagedWorkBasketInvalidQueueOperation
from publishing.models.loading_report import LoadingReport
from publishing.models.state import ProcessingState
from publishing.tasks import schedule_create_xml_envelope_file
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


def save_after(func):
    """
    Decorator used to save PackagedWorkBaskert instances after a state
    transition.

    This ensures a transitioned instance is always saved, which is necessary due
    to the DB updates that occur as part of a transition.
    """

    @atomic
    def inner(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save()
        return result

    return inner


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
            if top_before.envelope:
                top_before.envelope.delete()
                # so save_after does not throw foreign key restraint
                top_before.envelope = None
            PackagedWorkBasket.create_envelope_for_top()

        return result

    return inner


def skip_notifications_if_disabled(func):
    """Decorator used to wrap notification issuing functions, ensuring
    notifications are not sent when settings.ENABLE_PACKAGING_NOTIFICATIONS is
    False."""

    def inner(self, *args, **kwargs):
        if not settings.ENABLE_PACKAGING_NOTIFICATIONS:
            logger.info(
                "Skipping ready for processing notifications - "
                "settings.ENABLE_PACKAGING_NOTIFICATIONS="
                f"{settings.ENABLE_PACKAGING_NOTIFICATIONS}",
            )
            return
        logger.info(
            "Sending ready for processing notifications - "
            "settings.ENABLE_PACKAGING_NOTIFICATIONS="
            f"{settings.ENABLE_PACKAGING_NOTIFICATIONS}",
        )
        return func(self, *args, **kwargs)

    return inner


class PackagedWorkBasketManager(Manager):
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

    workbasket = ForeignKey(
        WorkBasket,
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
    loading_report = ForeignKey(
        LoadingReport,
        null=True,
        on_delete=PROTECT,
        editable=False,
    )
    """The report file associated with an attempt (either successful or failed)
    to process / load the associated workbasket's envelope file."""
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
    Operations (TOPS) project's Jira board.
    """
    create_envelope_task_id = CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )
    """ID of Celery task used to generate this instance's associated envelope.
    Its necessary to set null=True (unusually for CharField) in order to support
    the unique=True attribute."""

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

        self.processing_started_at = datetime.now()
        self.save()

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

    @skip_notifications_if_disabled
    def notify_ready_for_processing(self):
        """
        Notify users that an envelope is ready to download and process.

        This requires that the envelope has been generated and saved and is
        therefore normally called when the process for doing that has completed
        (see `publishing.tasks.create_xml_envelope_file()`).
        """

        personalisation = {
            "envelope_id": self.envelope.envelope_id,
            "download_url": (
                settings.BASE_SERVICE_URL + reverse("publishing:envelope-queue-ui-list")
            ),
            "theme": self.theme,
            "eif": self.eif if self.eif else "Immediately",
            "embargo": self.embargo if self.embargo else "None",
            "jira_url": self.jira_url,
        }
        send_emails.delay(
            template_id=settings.READY_FOR_CDS_TEMPLATE_ID,
            personalisation=personalisation,
        )

    @skip_notifications_if_disabled
    def notify_processing_succeeded(self):
        """
        Notify users that envelope processing has been succeeded for this.

        instance - correctly ingested into HMRC systems.
        """

        link_to_file = "None"
        if self.loading_report.file:
            f = self.loading_report.file.open("rb")
            link_to_file = prepare_upload(f)
        personalisation = {
            "envelope_id": self.envelope.envelope_id,
            "transaction_count": self.workbasket.transactions.count(),
            "link_to_file": link_to_file,
        }
        send_emails.delay(
            template_id=settings.CDS_ACCEPTED_TEMPLATE_ID,
            personalisation=personalisation,
        )

    @skip_notifications_if_disabled
    def notify_processing_failed(self):
        """Notify users that envelope processing has been failed - HMRC systems
        rejected this instances associated envelope file."""

        link_to_file = "None"
        if self.loading_report.file:
            f = self.loading_report.file.open("rb")
            link_to_file = prepare_upload(f)
        personalisation = {
            "envelope_id": self.envelope.envelope_id,
            "link_to_file": link_to_file,
        }
        send_emails.delay(
            template_id=settings.CDS_REJECTED_TEMPLATE_ID,
            personalisation=personalisation,
        )

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
    @create_envelope_on_new_top
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
    @create_envelope_on_new_top
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
    @create_envelope_on_new_top
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
    @create_envelope_on_new_top
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
