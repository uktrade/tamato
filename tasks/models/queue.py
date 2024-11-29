from __future__ import annotations

from typing import Self

from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.transaction import atomic

from common.util import TableLock
from common.util import get_related_names


class RequiredFieldError(Exception):
    pass


class Queue(models.Model):
    """
    A (FIFO) queue.

    Note: This abstract class only supports a single, reverse foreign-key relationship
    to `QueueItem` for each instance (i.e `QueueItem` instances are assumed to belong only to a single `Queue` instance).
    """

    class Meta:
        abstract = True

    def get_items(self) -> models.QuerySet:
        """Get all queue items as a queryset."""
        related_name = get_related_names(self, QueueItem)[0]
        return getattr(self, related_name).all()

    def get_first(self) -> QueueItem | None:
        """Get the first item in the queue."""
        return self.get_items().first()

    def get_last(self) -> QueueItem | None:
        """Get the last item in the queue."""
        return self.get_items().last()

    def get_item(self, position: int) -> QueueItem | None:
        """Get the item at `position` position in the queue."""
        try:
            return self.get_items().get(position=position)
        except ObjectDoesNotExist:
            return None

    @property
    def max_position(self) -> int:
        """
        Returns the highest item position in the queue.

        If the queue is empty it returns zero.
        """
        max = self.get_items().aggregate(
            max_position=models.Max("position"),
        )["max_position"]
        return max if max is not None else 0


class QueueItemMetaClass(models.base.ModelBase):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)

        if not new_class._meta.abstract:
            queue_field_name = getattr(new_class, "queue_field", None)
            cls.validate_queue_field(new_class, queue_field_name)
            cls.update_meta_ordering(new_class, queue_field_name)

        return new_class

    @staticmethod
    def update_meta_ordering(new_class: type[Self], queue_field_name: str) -> None:
        """Ensure the Meta.ordering attribute of `new_class` references the
        appropriate queue field."""
        inherited_queue_field = "queue"
        ordering = new_class._meta.ordering
        if (
            inherited_queue_field in ordering
            and queue_field_name != inherited_queue_field
        ):
            index = ordering.index(inherited_queue_field)
            ordering[index] = queue_field_name

    @staticmethod
    def validate_queue_field(new_class: type[Self], queue_field_name: str) -> None:
        """Validate that `new_class` has a `queue_field_name` ForeignKey field
        to a subclass of `Queue` model."""
        try:
            queue_field = new_class._meta.get_field(queue_field_name)
        except FieldDoesNotExist:
            queue_field = None

        if not queue_field or not isinstance(queue_field, models.ForeignKey):
            raise RequiredFieldError(
                f"{new_class.__name__} must have a 'queue' ForeignKey field. The name of the field must match the value given to the 'queue_field' attribute on the model.",
            )

        if not issubclass(queue_field.remote_field.model, Queue):
            raise RequiredFieldError(
                f"{queue_field} must be a ForeignKey field to a subclass of 'Queue' model.",
            )


class QueueItemManager(models.Manager):
    @atomic
    def create(self, **kwargs) -> QueueItem:
        """Create a new item instance in a queue, given by the `queue` named
        param, and place it in last position."""

        with TableLock(self.model, lock=TableLock.EXCLUSIVE):
            queue_field = self.model.queue_field
            queue = kwargs.pop(queue_field)
            position = kwargs.pop("position", (queue.get_items().count() + 1))

            if position <= 0:
                raise ValueError(
                    "QueueItem.position must be a positive integer greater than zero.",
                )

            return super().create(
                position=position,
                **{queue_field: queue},
                **kwargs,
            )


class QueueItem(models.Model, metaclass=QueueItemMetaClass):
    """Item that is a member of a Queue."""

    class Meta:
        abstract = True
        ordering = ["queue", "position"]

    queue_field: str = "queue"
    """
    The name of the required ForeignKey field relating this instance to a Queue
    instance.

    The value of this attribute can be inherited as is or overridden in
    subclasses to reflect the specific purpose or role of the queue.
    """

    position = models.PositiveSmallIntegerField(
        db_index=True,
        editable=False,
    )
    """
    1-based positioning - 1 is the first position.
    """

    objects = QueueItemManager()

    def get_queue_field(self) -> str:
        """Return the queue field name on this instance."""
        return self.__class__.queue_field

    def get_queue(self) -> type[Queue]:
        """Return the queue instance related to this instance."""
        return getattr(self, self.get_queue_field())

    @atomic
    def delete(self):
        """Remove and delete instance from its queue, shuffling all successive
        queued instances up one position."""
        instance = self.__class__.objects.select_for_update(nowait=True).get(pk=self.pk)

        self.__class__.objects.select_for_update(nowait=True).filter(
            position__gt=instance.position,
            **{self.get_queue_field(): self.get_queue()},
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
            **{self.get_queue_field(): self.get_queue()},
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

        queue_field = self.get_queue_field()
        queue = self.get_queue()
        queue_kwarg = {
            queue_field: queue,
        }

        if instance.position == queue.max_position:
            return instance

        item_to_promote = self.__class__.objects.select_for_update(nowait=True).get(
            position=instance.position + 1,
            **queue_kwarg,
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
            position__lt=instance.position,
            **{self.get_queue_field(): self.get_queue()},
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

        queue_field = self.get_queue_field()
        queue = self.get_queue()
        queue_kwarg = {
            queue_field: queue,
        }

        last_place = queue.max_position
        if instance.position == last_place:
            return instance

        self.__class__.objects.select_for_update(nowait=True).filter(
            position__gt=instance.position,
            **queue_kwarg,
        ).update(position=models.F("position") - 1)

        instance.position = last_place
        instance.save(update_fields=["position"])
        instance.refresh_from_db()

        return instance
