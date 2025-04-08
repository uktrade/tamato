from datetime import datetime
from typing import Self

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.urls import reverse
from django.utils.timezone import make_aware

from common.models.mixins import TimestampedMixin
from common.models.mixins import WithSignalManagerMixin
from common.models.mixins import WithSignalQuerysetMixin

User = get_user_model()


class ProgressState(models.Model):
    class State(models.TextChoices):
        TO_DO = "TO_DO", "To do"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    DEFAULT_STATE_NAME = State.TO_DO
    """The name of the default `State` object for `ProgressState`."""

    name = models.CharField(
        max_length=255,
        choices=State.choices,
        unique=True,
    )

    def __str__(self):
        return self.get_name_display()

    @classmethod
    def get_default_state_id(cls):
        """Get the id / pk of the default `State` object for `ProgressState`."""
        # Failsafe get_or_create() avoids attempt to get non-existant instance.
        default, _ = cls.objects.get_or_create(name=cls.DEFAULT_STATE_NAME)
        return default.id


class TaskManager(WithSignalManagerMixin, models.Manager):
    pass


class TaskQueryset(WithSignalQuerysetMixin, models.QuerySet):
    def non_workflow(self) -> "TaskQueryset":
        """Return a queryset of standalone Task instances that are not part of a
        workflow and are not subtasks."""
        return self.filter(
            models.Q(parent_task__isnull=True)
            & models.Q(taskitem__isnull=True)
            & models.Q(taskworkflow__isnull=True),
        )

    def workflow_summary(self) -> "TaskQueryset":
        """
        Return a queryset of summary Task instances of TaskWorkflows, i.e. those
        with a non-null related_name=taskworkflow.

        Summary Task instances are never subtasks.
        """
        return self.filter(
            models.Q(taskworkflow__isnull=False),
        )

    def top_level(self) -> "TaskQueryset":
        """
        Return a queryset of Task instances that are not subtasks and are
        either:
        1. Stand-alone Task instances that are not part of a Workflow tasks
        2. Workflow.summary_task instances.

        The intent is to provide a top-level filtering of Task instances,
        permitting a combined at-a-glance view of Tasks and Workflow instances.
        """
        return self.filter(
            (models.Q(taskitem__isnull=True) | models.Q(taskworkflow__isnull=False))
            & models.Q(parent_task__isnull=True),
        )

    def parents(self):
        """Returns a queryset of tasks who do not have subtasks linked to
        them."""
        return self.filter(
            models.Q(parent_task=None),
        )

    def subtasks(self):
        """Returns a queryset of tasks who have parent tasks linked to them."""
        return self.exclude(models.Q(parent_task=None))

    def incomplete(self):
        """Returns a queryset of tasks excluding those marked as complete."""
        return self.exclude(progress_state__name=ProgressState.State.DONE)

    def not_assigned_workflow(self):
        """Returns a queryset of summary Task instances that have never been assigned
        - with no associated TaskAssignee at all."""
        return self.filter(
            assignees__isnull=True,
        )

    def assigned(self):
        """Return the queryset of `Task` instances that have currently active
        assignees."""
        return self.filter(
            Q(assignees__isnull=False) & Q(assignees__unassigned_at__isnull=True),
        )

    def not_assigned(self):
        """
        Return the queryset of `Task` instances that currently have no active
        assignees. That is, they have either:

        - never had an assignee, or
        - had assignees, but they have now been unassigned.
        """
        active_assignees = TaskAssignee.objects.filter(unassigned_at__isnull=True)
        return self.exclude(assignees__in=active_assignees)

    def actively_assigned_to(self, user):
        """Returns a queryset of `Task` instances that have `user` currently
        assigned to them."""
        return self.filter(
            Q(assignees__user=user) & Q(assignees__unassigned_at__isnull=True),
        )

    def with_latest_assignees(self):
        """
        Returns a queryset of tasks annotated with the first_name of the most
        recent active TaskAssignee assigned to the Task.

        This allows for alphabetical ordering by Task assignee first_name
        """
        latest_assignees = TaskAssignee.objects.filter(
            task=OuterRef("pk"),
            unassigned_at__isnull=True,
        ).values("user__first_name")

        return self.annotate(assigned_user=Subquery(latest_assignees[:1]))


class TaskBase(TimestampedMixin):
    """Abstract model mixin containing model fields common to TaskTemplate and
    Task models."""

    class Meta:
        abstract = True

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(
        "Category",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )


class Task(TaskBase):
    progress_state = models.ForeignKey(
        ProgressState,
        default=ProgressState.get_default_state_id,
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
        "workbaskets.WorkBasket",
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

    objects = TaskManager.from_queryset(TaskQueryset)()

    class Meta(TaskBase.Meta):
        abstract = False
        ordering = ["id"]

    @property
    def has_automation(self) -> bool:
        """Return True if this task has an associated Automation instance, False
        otherwise."""
        return hasattr(self, "automation")

    @property
    @admin.display(boolean=True)
    def is_subtask(self) -> bool:
        return bool(self.parent_task)

    @property
    def is_summary_task(self) -> bool:
        return hasattr(self, "taskworkflow")

    def get_current_assignee(self) -> "TaskAssignee":
        """Returns the currently active`TaskAssignee` instance associated to
        this `Task` instance."""
        try:
            return self.assignees.assigned().get()
        except TaskAssignee.DoesNotExist:
            return TaskAssignee.objects.none()

    def get_workflow(self):
        """Return this task's TaskWorkflow instance if it has one, or otherwise
        returns None."""
        if self.is_summary_task:
            return self.taskworkflow
        elif hasattr(self, "taskitem"):
            return self.taskitem.workflow
        return None

    def __repr__(self):
        return f"{self.__class__}(pk={self.pk}, name={self.title})"

    def __str__(self):
        return self.title

    def get_url(self, action: str = "detail"):
        if action == "detail":
            return reverse("workflow:task-ui-detail", kwargs={"pk": self.pk})

        return "#NOT-IMPLEMENTED"


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


class TaskAssigneeManager(WithSignalManagerMixin, models.Manager):
    pass


class TaskAssigneeQueryset(WithSignalQuerysetMixin, models.QuerySet):
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
    """
    Model used to assocate Task instances with one or more Users.

    The original intent was to associate two mandatory user roles to a workbasket:
    - Worker who creates data in the workbasket - instances have
      `assignment_type = AssignmentType.WORKBASKET_WORKER`
    - Reviewer of workbasket data - instances have
      `assignment_type = AssignmentType.WORKBASKET_REVIEWER`

    In retrospect, these users should be assigned directly to the workbasket,
    not via a Task, which includes an unnecessary level of indirection.

    Current Task management introduces AssignmentType.GENERAL. TaskAssignee
    instances with
      `assignment_type = AssignmentType.GENERAL`
    are actual task assignments, rather than the legacy approach to assigning
    users to worker or reviewer roles.

    Workbasket and new task assignment should be separated by introducing a new
    Django Model, say, WorkBasketAssignee, and old assignments should be
    migrated to instances of the new, replacement model.

        class WorkBasketAssignee(TimestampedMixin):
            class AssignmentType(models.TextChoices):
                WORKBASKET_WORKER = "WORKBASKET_WORKER", "Workbasket worker"
                WORKBASKET_REVIEWER = "WORKBASKET_REVIEWER", "Workbasket reviewer"

            workbasket = models.ForeignKey(
                WorkBasket,
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="workbasketassignees",
            )
            user = models.ForeignKey(
                settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                related_name="assigned_to",
            )
            assignment_type = models.CharField(
                choices=AssignmentType.choices,
                max_length=50,
            )
            unassigned_at = models.DateTimeField(
                auto_now=False,
                blank=True,
                null=True,
            )

            @property
            def is_assigned(self) -> bool:
                return True if not self.unassigned_at else False

            @classmethod
            def unassign_user(cls, user, workbasket) -> bool:
                try:
                    assignment = cls.objects.get(user=user, workbasket=workbasket)
                except cls.DoesNotExist:
                    return False

                if assignment.unassigned_at:
                    return False

                with transaction.atomic():
                    assignment.unassigned_at = make_aware(datetime.now())
                    assignment.save(update_fields=["unassigned_at"])
                    return True

    AssignmentType can then be stripped from TaskAssignee, since there'll only
    be one type of assignee against tasks.
    """

    class AssignmentType(models.TextChoices):
        WORKBASKET_WORKER = "WORKBASKET_WORKER", "Workbasket worker"
        WORKBASKET_REVIEWER = "WORKBASKET_REVIEWER", "Workbasket reviewer"
        GENERAL = "GENERAL", "General"

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

    objects = TaskAssigneeManager.from_queryset(TaskAssigneeQueryset)()

    def __str__(self):
        return (
            f"User: {self.user} ({self.assignment_type}), " f"Task ID: {self.task.id}"
        )

    @property
    def is_assigned(self):
        return True if not self.unassigned_at else False

    @classmethod
    def unassign_user(cls, user, task, instigator) -> bool:
        """Unassigns the user from the given task by setting the
        TaskAssignee.unassigned_at field."""
        from tasks.signals import set_current_instigator

        try:
            assignment = cls.objects.assigned().get(user=user, task=task)
            set_current_instigator(instigator)
            with transaction.atomic():
                assignment.unassigned_at = make_aware(datetime.now())
                assignment.save(update_fields=["unassigned_at"])
            return True
        except cls.DoesNotExist:
            return False

    @classmethod
    def assign_user(cls, user, task: Task, instigator) -> Self:
        """Assigns a new user to the given task and unassigns the current
        assignee if one exists."""
        from tasks.signals import set_current_instigator

        set_current_instigator(instigator)

        current_assignee = task.get_current_assignee()

        if current_assignee:
            if current_assignee.user == user:
                return TaskAssignee.objects.none()

            cls.unassign_user(
                user=current_assignee.user,
                task=task,
                instigator=instigator,
            )

        return cls.objects.create(
            task=task,
            user=user,
            assignment_type=cls.AssignmentType.GENERAL,
        )


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
