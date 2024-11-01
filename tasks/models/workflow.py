from django.db import models
from django.db.transaction import atomic

from common.util import TableLock
from tasks.models.queue import Queue
from tasks.models.queue import QueueItem
from tasks.models.task import Task
from tasks.models.task import TaskBase

# ---------------
# - Base classes.
# ---------------


class TaskWorkflowBase(Queue):
    """Abstract model base class containing model fields common to TaskWorkflow
    and TaskWorkflowTemplate."""

    class Meta:
        abstract = True

    title = models.CharField(
        max_length=255,
    )
    description = models.TextField(
        blank=True,
    )


# ----------------------
# - Workflows and tasks.
# ----------------------


class TaskWorkflow(TaskWorkflowBase):
    """Workflow of ordered Tasks."""

    creator_template = models.ForeignKey(
        "tasks.TaskWorkflowTemplate",
        null=True,
        on_delete=models.SET_NULL,
    )
    parent_task = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
    )


class TaskItemManager(models.Manager):
    @atomic
    @TableLock.acquire_lock("tasks.TaskItem", lock=TableLock.EXCLUSIVE)
    def create(self, **kwargs) -> "TaskItem":
        """Create a new TaskItem instance in a workflow, given by the `queue`
        named param, and place it in last position."""

        task_workflow: TaskWorkflow = kwargs.pop("queue")

        return super().create(
            queue=task_workflow,
            # TODO: this'll be incorrect if all items haven't yet been saved.
            position=task_workflow.queue_items.count() + 1,
            **kwargs,
        )


class TaskItem(QueueItem):
    """Task item queue management for Task instances (these should always be
    subtasks)."""

    objects = TaskItemManager()
    subtask = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
    )
    """The subtask Task instance managed by this TaskItem."""


# ----------------------------------------
# - Template workflows and template tasks.
# ----------------------------------------


class TaskWorkflowTemplate(TaskWorkflowBase):
    """Template used to create TaskWorkflow instance."""

    # TODO: TableLock
    @atomic
    def create_task_workflow(self, parent_task) -> "TaskWorkflow":
        """Create a workflow and it subtasks, using values from this template
        workflow and its task templates."""

        task_workflow = TaskWorkflow.objects.create(
            title=self.title,
            description=self.description,
            creator_template=self,
            parent_task=parent_task,
        )

        task_item_templates = TaskItemTemplate.objects.filter(queue=self)
        for task_item_template in task_item_templates:
            subtask = Task.objects.create(
                title=task_item_template.title,
                description=task_item_template.description,
                category=task_item_template.category,
            )
            TaskItem.objects.create(
                queue=task_workflow,
                subtask=subtask,
            )

        return task_workflow


class TaskItemTemplateManager(models.Manager):
    @atomic
    @TableLock.acquire_lock("tasks.TaskItemTemplate", lock=TableLock.EXCLUSIVE)
    def create(self, **kwargs) -> "TaskItemTemplate":
        """Create a new TaskItemTemplate instance in a workflow, given by the
        `queue` named param, and place it in last position."""

        task_workflow_template: TaskWorkflowTemplate = kwargs.pop("queue")

        return super().create(
            queue=task_workflow_template,
            # TODO: this'll be incorrect if all items haven't yet been saved.
            position=task_workflow_template.queue_items.count() + 1,
            **kwargs,
        )


class TaskItemTemplate(QueueItem):
    """Queue item management for TaskTemplate instances."""

    objects = TaskItemTemplateManager()
    task_template = models.OneToOneField(
        "tasks.TaskTemplate",
        on_delete=models.CASCADE,
    )


class TaskTemplate(TaskBase):
    """Template used to create Task instances from within a template
    workflow."""
