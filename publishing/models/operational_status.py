from django.conf import settings
from django.db.models import PROTECT
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import Model
from django.db.models import QuerySet

from publishing.models.state import QueueState


class OperationalStatusQuerySet(QuerySet):
    def current_status(self):
        return self.order_by("pk").last()


class OperationalStatus(Model):
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

    created_at = DateTimeField(auto_now_add=True)
    created_by = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        editable=False,
        null=True,
    )
    """If a new instance is created as a result of direct user action (for
    instance pausing or unpausing the packaging queue) then `created_by` should
    be associated with that user."""
    queue_state = CharField(
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
