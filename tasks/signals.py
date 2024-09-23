import threading

from django.db.models.signals import pre_save
from django.dispatch import receiver

from tasks.models import Task
from tasks.models import TaskLog

_thread_locals = threading.local()


def get_current_instigator():
    return getattr(_thread_locals, "instigator", None)


def set_current_instigator(instigator):
    _thread_locals.instigator = instigator


@receiver(pre_save, sender=Task)
def create_tasklog_for_task_update(sender, instance, **kwargs):
    if not instance.pk:
        return

    old_instance = Task.objects.get(pk=instance.pk)

    if instance.progress_state != old_instance.progress_state:
        TaskLog.objects.create(
            task=instance,
            action=TaskLog.AuditActionType.PROGRESS_STATE_UPDATED,
            instigator=get_current_instigator(),
            progress_state=instance.progress_state,
        )
