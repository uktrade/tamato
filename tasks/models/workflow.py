from django.conf import settings
from django.db import models
from django.db.transaction import atomic
from django.urls import reverse

from common.models import User
from tasks.models.queue import Queue
from tasks.models.queue import QueueItem
from tasks.models.task import Task
from tasks.models.task import TaskBase

# ----------------------
# - Workflows and tasks.
# ----------------------


class TaskWorkflow(Queue):
    """Workflow of ordered Tasks."""

    summary_task = models.OneToOneField(
        Task,
        on_delete=models.PROTECT,
    )
    """Provides task-like filtering and display capabilities for this
    workflow."""
    creator_template = models.ForeignKey(
        "tasks.TaskWorkflowTemplate",
        null=True,
        on_delete=models.SET_NULL,
    )
    """The template from which this workflow was created, if any."""

    class Meta:
        verbose_name = "workflow"

    def __str__(self):
        return self.title

    @property
    def title(self) -> str:
        return self.summary_task.title

    @property
    def description(self) -> str:
        return self.summary_task.description

    def get_tasks(self) -> models.QuerySet:
        """Get a QuerySet of the Tasks associated through their TaskItem
        instances to this TaskWorkflow, ordered by the position of the
        TaskItem."""
        return Task.objects.filter(taskitem__queue=self).order_by("taskitem__position")

    def get_url(self, action: str = "detail"):
        if action == "detail":
            return reverse(
                "workflow:task-workflow-ui-detail",
                kwargs={"pk": self.pk},
            )
        elif action == "delete":
            return reverse(
                "workflow:task-workflow-ui-delete",
                kwargs={"pk": self.pk},
            )
        elif action == "create":
            return reverse(
                "workflow:task-workflow-ui-create",
            )
        elif action == "list":
            return reverse(
                "workflow:task-workflow-template-ui-list",
            )

        return "#NOT-IMPLEMENTED"


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


# ----------------------------------------
# - Template workflows and template tasks.
# ----------------------------------------


class TaskWorkflowTemplate(Queue):
    """Template used to create TaskWorkflow instance."""

    title = models.CharField(
        max_length=255,
    )
    """
    A title name for the instance.

    This isn't the same as the title assigned to a TaskWorkflow instance
    generated from a template.
    """
    description = models.TextField(
        blank=True,
        help_text="Description of what this workflow template is used for. ",
    )
    """
    Description of what the instance is used for.

    This isn't the same as the description that may be applied to a TaskWorkflow
    instance generated from a template.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="created_taskworkflowtemplates",
    )

    class Meta:
        verbose_name = "workflow template"

    def __str__(self):
        return self.title

    def get_task_templates(self) -> models.QuerySet:
        """Get a QuerySet of the TaskTemplates associated through their
        TaskItemTemplate instances to this TaskWorkflowTemplate, ordered by the
        position of the TaskItemTemplate."""
        return TaskTemplate.objects.filter(taskitemtemplate__queue=self).order_by(
            "taskitemtemplate__position",
        )

    @atomic
    def create_task_workflow(
        self,
        title: str,
        description: str,
        creator: User,
    ) -> "TaskWorkflow":
        """Create a workflow and it subtasks, using values from this template
        workflow and its task templates."""

        summary_task = Task.objects.create(
            title=title,
            description=description,
            creator=creator,
        )
        task_workflow = TaskWorkflow.objects.create(
            summary_task=summary_task,
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
                position=task_item_template.position,
                queue=task_workflow,
                task=task,
            )

        return task_workflow

    def get_url(self, action: str = "detail"):
        if action == "detail":
            return reverse(
                "workflow:task-workflow-template-ui-detail",
                kwargs={"pk": self.pk},
            )
        elif action == "edit":
            return reverse(
                "workflow:task-workflow-template-ui-update",
                kwargs={"pk": self.pk},
            )
        elif action == "delete":
            return reverse(
                "workflow:task-workflow-template-ui-delete",
                kwargs={"pk": self.pk},
            )
        elif action == "create":
            return reverse(
                "workflow:task-workflow-template-ui-create",
            )

        return "#NOT-IMPLEMENTED"


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


class TaskTemplate(TaskBase):
    """Template used to create Task instances from within a template
    workflow."""

    def get_url(self, action: str = "detail"):
        if action == "detail":
            return reverse("workflow:task-template-ui-detail", kwargs={"pk": self.pk})
        elif action == "edit":
            return reverse("workflow:task-template-ui-update", kwargs={"pk": self.pk})
        elif action == "delete":
            return reverse(
                "workflow:task-template-ui-delete",
                kwargs={
                    "workflow_template_pk": self.taskitemtemplate.queue.pk,
                    "pk": self.pk,
                },
            )

        return "#NOT-IMPLEMENTED"

    def __str__(self):
        return self.title
