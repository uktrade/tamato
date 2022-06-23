"""
Provide a way to link a Celery Task (usually referencable from a UUID) to a
django Model.

This enables retrieving the realtime status of tasks while they are running.

Once tasks have completed, these models should be deleted.
"""

from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from django.db import models
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet

from common.celery import app as celery_app

logger = get_task_logger(__name__)


class TaskModel(PolymorphicModel):
    """
    Mixin for models that can be linked to a celery task.

    All celery specific functionality is at the other end of the relationship,
    on ModelCeleryTask, leaving an extension point for other non-celery based
    implementations.
    """


class ModelCeleryTaskQuerySet(PolymorphicQuerySet):
    def filter_by_task_status(self, statuses=None):
        """
        Note:  Passing in task ids that are not known to Celery will return Tasks with 'PENDING' status,
        as celery can't know if these are tasks that have not reached the broker yet or just don't exist.
        """
        model_task_ids = (
            model_task.pk
            for model_task in self
            if statuses is None or model_task.get_celery_task_status() in statuses
        )

        return self.filter(pk__in=model_task_ids)

    def filter_by_task_kwargs(self, **kwargs):
        def task_kwargs_match(task):
            """
            :return: True if all the specified kwargs match those on the task.
            """
            if task.kwargs is None:
                return False

            for k, v in kwargs.items():
                if k not in task.kwargs or task.kwargs[k] != v:
                    return False
            return True

        model_task_ids = (
            model_task.pk
            for model_task in self
            if task_kwargs_match(model_task.get_celery_task())
        )

        return self.filter(pk__in=model_task_ids)

    def filter_by_task_args(self, *args):
        model_task_ids = (
            model_task.pk
            for model_task in self
            if model_task.get_celery_task().result.args == args
        )

        return self.filter(pk__in=model_task_ids)

    def update_task_statuses(self):
        """Update the last_task_status of all modeltasks in the queryset from
        celery."""
        model_tasks = self  # .all()
        for model_task in model_tasks:
            task_status = model_task.get_celery_task_status()
            # 'PENDING' can mean the task is not yet known to celery,
            # or it is a task that has not yet reached the broker, if
            # the status goes *back* to 'PENDING' from a higher status
            # then don't forget it the higher status.
            if not model_task.last_task_status or task_status != "PENDING":
                model_task.last_task_status = task_status

        self.model.objects.bulk_update(
            model_tasks,
            ["last_task_status"],
            batch_size=2000,
        )
        return model_tasks

    def delete_pending_tasks(self):
        """"""
        return self.filter_by_task_status("PENDING").delete()

    def revoke(self, **kwargs):
        for task_id in self.values_list("celery_task_id", flat=True):
            task = AsyncResult(task_id)
            task.revoke(**kwargs)

        self.delete()


class ModelCeleryTask(PolymorphicModel):
    """
    Provide a way to link a Celery Task (usually referencable from a UUID) to a
    django Model.

    ModelCeleryTask instances should be created at the same time as the Celery Task they are
    linked to.

    This is because 'PENDING' in Celery either means the task is queued or is returned for unknown
    tasks.
    """

    class Meta:
        unique_together = ("celery_task_id", "object")

    objects = ModelCeleryTaskQuerySet.as_manager()

    celery_task_name = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )
    celery_task_id = models.CharField(max_length=64, db_index=True)
    last_task_status = models.CharField(max_length=8)

    object = models.ForeignKey(
        "common.TaskModel",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    def get_celery_task(self):
        """Get a reference to the Celery task instance."""
        return celery_app.AsyncResult(self.celery_task_id)

    def get_celery_task_status(self):
        """Query celery and return the task status."""
        return self.get_celery_task().status

    @classmethod
    def bind_model(cls, object: TaskModel, celery_task_id: str, celery_task_name: str):
        """Link a Celery Task UUID to a django Model."""
        model_task, created = ModelCeleryTask.objects.get_or_create(
            {"celery_task_name": celery_task_name},
            object=object,
            celery_task_id=celery_task_id,
        )
        if not created:
            # Call save to update the last_task_status from celery.
            # (on creation, save will have been called by django)
            model_task.save()

        logger.debug("Bound celery task %s to %s", celery_task_id, object)
        return model_task

    @classmethod
    def unbind_model(cls, object: TaskModel):
        """Unlink a Celery Task UUID from a django Model."""
        return ModelCeleryTask.objects.filter(
            object=object,
        ).delete()

    def save(self, *args, **kwargs):
        """Override save to update the last_task_status from celery."""
        task_status = self.get_celery_task_status()
        if not self.last_task_status or task_status != "PENDING":
            # 'PENDING' can mean the task is not yet known to celery,
            # or it is a task that has not yet reached the broker, if
            # the status goes *back* to 'PENDING' from a higher status
            # then don't forget it the higher status.
            self.last_task_status = task_status
        super().save(*args, **kwargs)

    def __repr__(self):
        return f"<ModelCeleryTask {self.celery_task_name} [{self.celery_task_id}] status={self.last_task_status}>"


def bind_model_task(object: TaskModel, celery_task_id: str, celery_task_name: str):
    """Link a Celery Task UUID to a PolymorphicModel instance."""
    return ModelCeleryTask.bind_model(object, celery_task_id, celery_task_name)


def unbind_model_task(object: TaskModel):
    """Link a Celery Task UUID to a PolymorphicModel model instance."""
    return ModelCeleryTask.unbind_model(object)
