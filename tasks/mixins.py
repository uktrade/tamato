from django.db import OperationalError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property

from tasks.models import Queue
from tasks.models import QueueItem
from tasks.models import Task


class QueuedItemManagementMixin:
    """A view mixin providing helper functions to manage queued items."""

    queued_item_model: type[QueueItem] = None
    """The model responsible for managing members of a queue."""

    item_lookup_field: str = ""
    """The lookup field of the instance managed by a queued item."""

    queue_field: str = ""
    """The name of the ForeignKey field relating a queued item to a queue."""

    @cached_property
    def queue(self) -> type[Queue]:
        """The queue instance that is the object of the view."""
        return self.get_object()

    def promote(self, lookup_id: int) -> None:
        queued_item = get_object_or_404(
            self.queued_item_model,
            **{
                self.item_lookup_field: lookup_id,
                self.queue_field: self.queue,
            },
        )
        try:
            queued_item.promote()
        except OperationalError:
            pass

    def demote(self, lookup_id: int) -> None:
        queued_item = get_object_or_404(
            self.queued_item_model,
            **{
                self.item_lookup_field: lookup_id,
                self.queue_field: self.queue,
            },
        )
        try:
            queued_item.demote()
        except OperationalError:
            pass

    def promote_to_first(self, lookup_id: int) -> None:
        queued_item = get_object_or_404(
            self.queued_item_model,
            **{
                self.item_lookup_field: lookup_id,
                self.queue_field: self.queue,
            },
        )
        try:
            queued_item.promote_to_first()
        except OperationalError:
            pass

    def demote_to_last(self, lookup_id: int) -> None:
        queued_item = get_object_or_404(
            self.queued_item_model,
            **{
                self.item_lookup_field: lookup_id,
                self.queue_field: self.queue,
            },
        )
        try:
            queued_item.demote_to_last()
        except OperationalError:
            pass


class TaskAssignmentMixin:
    template_name = template_name = "tasks/assign_users.jinja"

    @cached_property
    def task(self):
        return Task.objects.get(pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["task"] = self.task
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Assign user to step"
        context["ticket"] = self.task.taskitem.workflow
        context["step"] = self.task
        return context

    def get_success_url(self):
        return reverse(
            "workflow:task-ui-detail",
            kwargs={"pk": self.kwargs["pk"]},
        )
