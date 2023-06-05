from django.conf import settings
from django.db.models import PROTECT
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import Model
from django.db.models import QuerySet

from publishing.models.state import CrownDependenciesPublishingState
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


class CrownDependenciesPublishingOperationalStatus(Model):
    """
    Operational status of the Crown Dependencies envelope publishing task.

    The publishing task may be: unpaused, which allows publishing of Crown
    Dependencies envelopes; or paused, which blocks publishing until unpaused.
    """

    class Meta:
        ordering = ["pk"]
        verbose_name_plural = "crown dependencies publishing operational statuses"

    objects = OperationalStatusQuerySet.as_manager()

    created_at = DateTimeField(auto_now_add=True)
    created_by = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        editable=False,
        null=True,
    )
    publishing_state = CharField(
        max_length=8,
        default=CrownDependenciesPublishingState.PAUSED,
        choices=CrownDependenciesPublishingState.choices,
    )

    @classmethod
    def pause_publishing(
        cls,
        user: settings.AUTH_USER_MODEL,
    ) -> "CrownDependenciesPublishingOperationalStatus":
        """
        Transition operational status of publishing into a paused state (if it
        is not already paused) by creating a new
        `CrownDependenciesPublishingOperationalStatus` and returning it to the
        caller.

        If publishing is already paused, then do nothing and return None.
        """
        if cls.is_publishing_paused():
            return None
        return CrownDependenciesPublishingOperationalStatus.objects.create(
            publishing_state=CrownDependenciesPublishingState.PAUSED,
            created_by=user,
        )

    @classmethod
    def unpause_publishing(
        cls,
        user: settings.AUTH_USER_MODEL,
    ) -> "CrownDependenciesPublishingOperationalStatus":
        """
        Transition operational status of publishing into an unpaused state (if
        it is not already unpaused) by creating a new
        `CrownDependenciesPublishingOperationalStatus` and returning it to the
        caller.

        If publishing is already unpaused, then do nothing and return None.
        """
        if not cls.is_publishing_paused():
            return None
        return CrownDependenciesPublishingOperationalStatus.objects.create(
            publishing_state=CrownDependenciesPublishingState.UNPAUSED,
            created_by=user,
        )

    @classmethod
    def is_publishing_paused(cls) -> bool:
        """Returns True if publishing is paused, False otherwise."""
        current_status = cls.objects.current_status()
        if (
            not current_status
            or current_status.publishing_state
            == CrownDependenciesPublishingState.PAUSED
        ):
            return True
        else:
            return False
