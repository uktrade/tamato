from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from common.models.mixins import TimestampedMixin
from tasks.models.task import Task

User = get_user_model()


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
        null=True,
        on_delete=models.SET_NULL,
        editable=False,
        related_name="logs",
    )
    instigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
    )

    objects = TaskLogManager()
