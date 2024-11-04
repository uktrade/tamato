from django.db import models
from django.db.transaction import atomic


class Queue(models.Model):
    """A (FIFO) queue."""

    class Meta:
        abstract = True

    def get_first(self) -> "QueueItem":
        """Get the first item in the queue."""
        # TODO

    def get_last(self) -> "QueueItem":
        """Get the last item in the queue."""
        # TODO

    def get_item(self, position: int) -> "QueueItem":
        """Get the item at `position` position in the queue."""
        # TODO


class QueueItem(models.Model):
    """Item that is a member of a Queue."""

    class Meta:
        abstract = True
        ordering = ["queue", "position"]

    """The Queue that this instance is a member of."""
    position = models.PositiveSmallIntegerField(
        db_index=True,
        editable=False,
    )
    """
    1-based positioning - 1 is the first position.
    """

    @atomic
    def delete(self):
        """Remove and delete instance from its queue, shuffling all successive
        queued instances up one position."""
        # TODO

    @atomic
    def promote(self):
        """
        Promote the instance by one place up the queue.

        No change is made if the instance is already in its queue's first place.
        """
        # TODO

    @atomic
    def demote(self):
        """
        Demote the instance by one place down the queue.

        No change is made if the instance is already in its queue's last place.
        """
        # TODO

    @atomic
    def promote_to_first(self):
        """Promote the instance to the first place in the queue so that it
        occupies position 1."""
        # TODO

    @atomic
    def demote_to_last(self):
        """
        Demote the instance to the last place in the queue so that it occupies
        position of queue length.

        No change is made if the instance is already in its queue's last place.
        """
        # TODO
