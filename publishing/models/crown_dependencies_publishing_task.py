import logging

from celery.result import AsyncResult
from django.db.models import CharField

from common.models.mixins import TimestampedMixin

logger = logging.getLogger(__name__)


class CrownDependenciesPublishingTask(TimestampedMixin):
    """Represents a Celery task that publishes `CrownDependenciesEnvelope`."""

    class Meta:
        ordering = ("pk",)

    task_id = CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )

    @property
    def task_status(self):
        """Return the status of the publishing task if it is available,
        otherwise return None."""
        if not self.task_id:
            return None
        task_result = AsyncResult(self.task_id)
        if not task_result:
            return None
        return task_result.status

    def terminate_task(self):
        """Terminate the publishing task as identified by its task_id."""
        logger.info(
            f"Attempting publishing task termination pk={self.pk}.",
        )
        if not self.task_id:
            logger.info(
                f"Unable to terminate publishing task "
                f"pk={self.pk} - "
                f"empty task_id.",
            )
            return

        task_result = AsyncResult(self.task_id)
        if not task_result:
            logger.info(
                f"Unable to terminate publishing task "
                f"pk={self.pk}, "
                f"task_id={self.task_id} - "
                f"task result is unavailable.",
            )
            return

        task_result.revoke()
        self.task_id = None
        self.save()
        logger.info(
            f"Terminated publishing task pk={self.pk}.",
        )

    def __repr__(self) -> str:
        return (
            f'<CrownDependenciesPublishingTask: id="{self.pk}", task_id={self.task_id}>'
        )
