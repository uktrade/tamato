import threading

from django.db.models.signals import pre_save
from django.dispatch import receiver

from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskLog

_thread_locals = threading.local()


def get_current_instigator():
    return getattr(_thread_locals, "instigator", None)


def set_current_instigator(instigator):
    _thread_locals.instigator = instigator


@receiver(pre_save, sender=Task)
def create_tasklog_for_task_update(sender, instance, old_instance=None, **kwargs):
    """
    Creates a `TaskLog` entry when a `Task` is being updated and the update
    action is a `TaskLog.AuditActionType`.

    Note that this signal is triggered before the `Task` instance is saved.
    """
    if instance._state.adding:
        return

    old_instance = old_instance or Task.objects.get(pk=instance.pk)

    if instance.progress_state != old_instance.progress_state:
        TaskLog.objects.create(
            task=instance,
            action=TaskLog.AuditActionType.PROGRESS_STATE_UPDATED,
            instigator=get_current_instigator(),
            progress_state=instance.progress_state,
        )


@receiver(pre_save, sender=TaskAssignee)
def create_tasklog_for_task_assignee(sender, instance, old_instance=None, **kwargs):
    """
    Creates a `TaskLog` entry when a user is assigned to or unassigned from a
    `Task`.

    Note that this signal is triggered before the `TaskAssignee` instance is saved.
    """
    if instance._state.adding:
        return TaskLog.objects.create(
            task=instance.task,
            action=TaskLog.AuditActionType.TASK_ASSIGNED,
            instigator=get_current_instigator(),
            assignee=instance.user,
        )

    old_instance = old_instance or TaskAssignee.objects.get(pk=instance.pk)

    if instance.unassigned_at and instance.unassigned_at != old_instance.unassigned_at:
        return TaskLog.objects.create(
            task=instance.task,
            action=TaskLog.AuditActionType.TASK_UNASSIGNED,
            instigator=get_current_instigator(),
            assignee=old_instance.user,
        )
