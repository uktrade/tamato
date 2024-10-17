from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from common.models.mixins import TimestampedMixin
from workbaskets.models import WorkBasket

User = get_user_model()


class Task(TimestampedMixin):
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(
        "Category",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    progress_state = models.ForeignKey(
        "ProgressState",
        on_delete=models.PROTECT,
    )
    parent_task = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )
    workbasket = models.ForeignKey(
        WorkBasket,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )

    def __str__(self):
        return self.title


class Category(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class ProgressState(models.Model):
    class State(models.TextChoices):
        TO_DO = "TO_DO", "To do"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    name = models.CharField(
        max_length=255,
        choices=State.choices,
        unique=True,
    )

    def __str__(self):
        return self.get_name_display()


class TaskAssigneeQueryset(models.QuerySet):
    def assigned(self):
        return self.exclude(unassigned_at__isnull=False)

    def unassigned(self):
        return self.exclude(unassigned_at__isnull=True)

    def workbasket_workers(self):
        return self.filter(
            assignment_type=TaskAssignee.AssignmentType.WORKBASKET_WORKER,
        )

    def workbasket_reviewers(self):
        return self.filter(
            assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
        )


class TaskAssignee(TimestampedMixin):
    class AssignmentType(models.TextChoices):
        WORKBASKET_WORKER = "WORKBASKET_WORKER", "Workbasket worker"
        WORKBASKET_REVIEWER = "WORKBASKET_REVIEWER", "Workbasket reviewer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_to",
    )
    assignment_type = models.CharField(
        choices=AssignmentType.choices,
        max_length=50,
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        editable=False,
        related_name="assignees",
    )
    unassigned_at = models.DateTimeField(
        auto_now=False,
        blank=True,
        null=True,
    )

    objects = TaskAssigneeQueryset.as_manager()

    def __str__(self):
        return (
            f"User: {self.user} ({self.assignment_type}), " f"Task ID: {self.task.id}"
        )

    @property
    def is_assigned(self):
        return True if not self.unassigned_at else False

    @classmethod
    def unassign_user(cls, user, task):
        try:
            assignment = cls.objects.get(user=user, task=task)
            if assignment.unassigned_at:
                return False
            assignment.unassigned_at = datetime.now()
            assignment.save(update_fields=["unassigned_at"])
            return True
        except cls.DoesNotExist:
            return False


class TaskLogManager(models.Manager):
    def create(
        self,
        task: Task,
        action: "TaskLog.AuditActionType",
        instigator: User,
        **kwargs,
    ) -> "TaskLog":
        """
        Creates a new `TaskLog` instance with a generated description based on
        `action`, saving it to the database and returning the created instance.

        A TaskLog's `description` is generated using a template retrieved from `TaskLog.AUDIT_ACTION_MAP` that maps an `action` to its corresponding description.
        Additional `kwargs` are required to format the description template depending on the provided action.
        """

        if action not in self.model.AuditActionType:
            raise ValueError(
                f"The action '{action}' is an invalid TaskLog.AuditActionType value.",
            )

        description_template = self.model.AUDIT_ACTION_MAP.get(action)
        if not description_template:
            raise ValueError(
                f"No description template found for action '{action}' in TaskLog.AUDIT_ACTION_MAP.",
            )

        context = {"instigator": instigator}

        if action in {
            self.model.AuditActionType.TASK_ASSIGNED,
            self.model.AuditActionType.TASK_UNASSIGNED,
        }:
            assignee = kwargs.pop("assignee", None)
            if not assignee:
                raise ValueError(f"Missing 'assignee' in kwargs for action '{action}'.")
            context["assignee"] = assignee

        elif action == self.model.AuditActionType.PROGRESS_STATE_UPDATED:
            progress_state = kwargs.pop("progress_state", None)
            if not progress_state:
                raise ValueError(
                    f"Missing 'progress_state' in kwargs for action '{action}'.",
                )
            context["progress_state"] = progress_state

        description = description_template.format(**context)

        return super().create(
            task=task,
            action=action,
            instigator=instigator,
            description=description,
            **kwargs,
        )


class TaskLog(TimestampedMixin):
    class AuditActionType(models.TextChoices):
        TASK_ASSIGNED = ("TASK_ASSIGNED",)
        TASK_UNASSIGNED = ("TASK_UNASSIGNED",)
        PROGRESS_STATE_UPDATED = ("PROGRESS_STATE_UPDATED",)

    AUDIT_ACTION_MAP = {
        AuditActionType.TASK_ASSIGNED: "{instigator} assigned {assignee}",
        AuditActionType.TASK_UNASSIGNED: "{instigator} unassigned {assignee}",
        AuditActionType.PROGRESS_STATE_UPDATED: "{instigator} changed the status to {progress_state}",
    }

    action = models.CharField(
        max_length=100,
        choices=AuditActionType.choices,
        editable=False,
    )
    description = models.TextField(editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        editable=False,
        related_name="logs",
    )
    instigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
    )

    objects = TaskLogManager()


class Comment(TimestampedMixin):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        related_name="authored_comments",
    )
    content = models.TextField(
        max_length=1000 * 5,  # Max words * average character word length.
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        editable=False,
        related_name="comments",
    )
