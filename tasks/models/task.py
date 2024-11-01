from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
from django.urls import reverse

from common.models.mixins import TimestampedMixin
from common.models.mixins import WithSignalManagerMixin
from common.models.mixins import WithSignalQuerysetMixin
from workbaskets.models import WorkBasket

User = get_user_model()


class TaskManager(WithSignalManagerMixin, models.Manager):
    pass


class TaskQueryset(WithSignalQuerysetMixin, models.QuerySet):
    pass


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

    objects = TaskManager.from_queryset(TaskQueryset)()

    def __str__(self):
        return self.title

    def get_url(self):
        return reverse("workflow:task-ui-detail", kwargs={"pk": self.pk})


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

    objects = TaskAssigneeManager.from_queryset(TaskAssigneeQueryset)()

    def __str__(self):
        return (
            f"User: {self.user} ({self.assignment_type}), " f"Task ID: {self.task.id}"
        )

    @property
    def is_assigned(self):
        return True if not self.unassigned_at else False

    @classmethod
    def unassign_user(cls, user, task, instigator):
        from tasks.signals import set_current_instigator

        try:
            assignment = cls.objects.get(user=user, task=task)
            if assignment.unassigned_at:
                return False
            set_current_instigator(instigator)
            with transaction.atomic():
                assignment.unassigned_at = datetime.now()
                assignment.save(update_fields=["unassigned_at"])
            return True
        except cls.DoesNotExist:
            return False


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
