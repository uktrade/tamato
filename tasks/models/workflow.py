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


class TaskItemManager(models.Manager):
    @atomic
    @TableLock.acquire_lock("tasks.TaskItem", lock=TableLock.EXCLUSIVE)
    def create(self, **kwargs) -> "TaskItem":
        """Create a new TaskItem instance in a workflow, given by the `queue`
        named param, and place it in last position."""

        task_workflow: TaskWorkflow = kwargs.pop("queue")
        position = kwargs.pop("position", (task_workflow.queue_items.count() + 1))

        if position <= 0:
            raise ValueError(
                "TaskItem.position must be a positive integer greater than zero.",
            )

        return super().create(
            queue=task_workflow,
            position=position,
            **kwargs,
        )


class TaskItem(QueueItem):
    """Task item queue management for Task instances (these should always be
    subtasks)."""

    queue = models.ForeignKey(
        TaskWorkflow,
        related_name="queue_items",
        on_delete=models.CASCADE,
    )
    task = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
    )
    """The Task instance managed by this TaskItem."""

    objects = TaskItemManager()


# ----------------------------------------
# - Template workflows and template tasks.
# ----------------------------------------


class TaskWorkflowTemplate(TaskWorkflowBase):
    """Template used to create TaskWorkflow instance."""

    @atomic
    def create_task_workflow(self) -> "TaskWorkflow":
        """Create a workflow and it subtasks, using values from this template
        workflow and its task templates."""

        task_workflow = TaskWorkflow.objects.create(
            title=self.title,
            description=self.description,
            creator_template=self,
        )

        task_item_templates = TaskItemTemplate.objects.select_related(
            "task_template",
        ).filter(queue=self)
        for task_item_template in task_item_templates:
            task_template = task_item_template.task_template
            task = Task.objects.create(
                title=task_template.title,
                description=task_template.description,
                category=task_template.category,
            )
            TaskItem.objects.create(
                position=task_template.position,
                queue=task_workflow,
                task=task,
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
            position=task_workflow_template.queue_items.count() + 1,
            **kwargs,
        )


class TaskItemTemplate(QueueItem):
    """Queue item management for TaskTemplate instances."""

    queue = models.ForeignKey(
        TaskWorkflowTemplate,
        related_name="queue_items",
        on_delete=models.CASCADE,
    )
    task_template = models.OneToOneField(
        "tasks.TaskTemplate",
        on_delete=models.CASCADE,
    )

    objects = TaskItemTemplateManager()


class TaskTemplate(TaskBase):
    """Template used to create Task instances from within a template
    workflow."""
