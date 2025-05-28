"""Mixins for models."""

from django.db import models
from django.db.models import signals


class TimestampedMixin(models.Model):
    """Mixin adding timestamps for creation and last update."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WithSignalManagerMixin:
    """A mixin that overrides default Manager methods to send pre_save signals
    for model instances."""

    def bulk_create(self, objs, **kwargs) -> list:
        for obj in objs:
            signals.pre_save.send(sender=self.model, instance=obj)
        return super().bulk_create(objs, **kwargs)


class WithSignalQuerysetMixin:
    """A mixin that overrides default QuerySet methods to send pre_save signals
    for model instances."""

    def update(self, **kwargs) -> int:
        old_instances_map = {}
        pk_list = []
        for old_instance in self.iterator():
            old_instances_map[old_instance.pk] = old_instance
            pk_list.append(old_instance.pk)

        rows_updated = super().update(**kwargs)

        for new_instance in self.model.objects.filter(pk__in=pk_list):
            old_instance = old_instances_map.get(new_instance.pk)
            signals.pre_save.send(
                sender=self.model,
                instance=new_instance,
                old_instance=old_instance,
            )

        return rows_updated
