from __future__ import annotations

from typing import Self

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.transaction import atomic

from common.util import TableLock
from common.util import get_related_objects


class RequiredFieldError(Exception):
    pass


class Queue(models.Model):
    """A (FIFO) queue."""

    class Meta:
        abstract = True

    def get_items(self) -> models.QuerySet:
        """Get all queue items as a queryset."""
        return get_related_objects(self, QueueItem)

    def get_first(self) -> QueueItem | None:
        """Get the first item in the queue."""
        return get_related_objects(self, QueueItem).first()

    def get_last(self) -> QueueItem | None:
        """Get the last item in the queue."""
        return get_related_objects(self, QueueItem).last()

    def get_item(self, position: int) -> QueueItem | None:
        """Get the item at `position` position in the queue."""
        try:
            return get_related_objects(self, QueueItem).get(position=position)
        except ObjectDoesNotExist:
            return None

    @property
    def max_position(self) -> int:
        """
        Returns the highest item position in the queue.

        If the queue is empty it returns zero.
        """
        max = get_related_objects(self, QueueItem).aggregate(
            max_position=models.Max("position"),
        )["max_position"]
        return max if max is not None else 0


class QueueItemMetaClass(models.base.ModelBase):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)

        if (
            "QueueItem" in [base.__name__ for base in bases]
            and not new_class._meta.abstract
        ):
            queue_field = attrs.get("queue", None)
            if not queue_field or not isinstance(queue_field, models.ForeignKey):
                raise RequiredFieldError(
                    f"{name} must have a 'queue' ForeignKey field.",
                )

        return new_class


class QueueItemManager(models.Manager):
    @atomic
    def create(self, **kwargs) -> QueueItem:
        """Create a new item instance in a queue, given by the `queue` named
        param, and place it in last position."""

        with TableLock(self.model, lock=TableLock.EXCLUSIVE):
            queue = kwargs.pop("queue")
            position = kwargs.pop("position", (queue.get_items().count() + 1))

            if position <= 0:
                raise ValueError(
                    "QueueItem.position must be a positive integer greater than zero.",
                )

            return super().create(
                queue=queue,
                position=position,
                **kwargs,
            )


class QueueItem(models.Model, metaclass=QueueItemMetaClass):
    """Item that is a member of a Queue."""

    class Meta:
        abstract = True
        ordering = ["queue", "position"]

    position = models.PositiveSmallIntegerField(
        db_index=True,
        editable=False,
    )
    """
    1-based positioning - 1 is the first position.
    """

    objects = QueueItemManager()

    @atomic
    def delete(self):
        """Remove and delete instance from its queue, shuffling all successive
        queued instances up one position."""
        instance = self.__class__.objects.select_for_update(nowait=True).get(pk=self.pk)

        self.__class__.objects.select_for_update(nowait=True).filter(
            position__gt=instance.position,
        ).update(position=models.F("position") - 1)

        return super().delete()

    @atomic
    def promote(self) -> Self:
        """
        Promote the instance by one place up the queue.

        No change is made if the instance is already in its queue's first place.

        Returns the promoted instance with any database updates applied.
        """
        instance = self.__class__.objects.select_for_update(nowait=True).get(pk=self.pk)

        if instance.position == 1:
            return instance

        item_to_demote = self.__class__.objects.select_for_update(nowait=True).get(
            position=instance.position - 1,
        )
        item_to_demote.position += 1
        instance.position -= 1
        self.__class__.objects.bulk_update([instance, item_to_demote], ["position"])
        instance.refresh_from_db()

        return instance

    @atomic
    def demote(self) -> Self:
        """
        Demote the instance by one place down the queue.

        No change is made if the instance is already in its queue's last place.

        Returns the demoted instance with any database updates applied.
        """
        instance = self.__class__.objects.select_for_update(nowait=True).get(pk=self.pk)

        if instance.position == self.queue.max_position:
            return instance

        item_to_promote = self.__class__.objects.select_for_update(nowait=True).get(
            position=instance.position + 1,
        )
        item_to_promote.position -= 1
        instance.position += 1
        self.__class__.objects.bulk_update([instance, item_to_promote], ["position"])
        instance.refresh_from_db()

        return instance

    @atomic
    def promote_to_first(self) -> Self:
        """
        Promote the instance to the first place in the queue so that it occupies
        position 1.

        No change is made if the instance is already in its queue's first place.

        Returns the promoted instance with any database updates applied.
        """

        instance = self.__class__.objects.select_for_update(nowait=True).get(pk=self.pk)

        if instance.position == 1:
            return instance

        self.__class__.objects.select_for_update(nowait=True).filter(
            models.Q(position__lt=instance.position),
        ).update(position=models.F("position") + 1)

        instance.position = 1
        instance.save(update_fields=["position"])
        instance.refresh_from_db()

        return instance

    @atomic
    def demote_to_last(self) -> Self:
        """
        Demote the instance to the last place in the queue so that it occupies
        position of queue length.

        No change is made if the instance is already in its queue's last place.

        Returns the demoted instance with any database updates applied.
        """
        instance = self.__class__.objects.select_for_update(nowait=True).get(pk=self.pk)

        last_place = self.queue.max_position
        if instance.position == last_place:
            return instance

        self.__class__.objects.select_for_update(nowait=True).filter(
            position__gt=instance.position,
        ).update(position=models.F("position") - 1)

        instance.position = last_place
        instance.save(update_fields=["position"])
        instance.refresh_from_db()

        return instance
