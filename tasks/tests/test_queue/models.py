from django.db import models

from tasks.models import Queue
from tasks.models import QueueItem


class TestQueue(Queue):
    """Concrete subclass of Queue."""

    class Meta:
        abstract = False


class TestQueueItem(QueueItem):
    """Concrete subclass of QueueItem."""

    class Meta:
        abstract = False

    queue_field = "queue"

    queue = models.ForeignKey(
        TestQueue,
        related_name="queue_items",
        on_delete=models.CASCADE,
    )
