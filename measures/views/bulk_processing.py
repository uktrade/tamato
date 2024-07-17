from typing import Dict

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.detail import DetailView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

from common.views import WithPaginationListView
from measures import models
from measures.filters import MeasureCreateTaskFilter
from measures.forms import CancelBulkProcessorTaskForm
from measures.models.bulk_processing import MeasuresBulkCreator
from measures.models.bulk_processing import ProcessingState
from workbaskets.validators import WorkflowStatus


class CancelBulkProcessorTask(
    UserPassesTestMixin,
    SingleObjectMixin,
    FormView,
):
    """Attempt cancelling a bulk processor task."""

    permission_required = "measures.edit_bulkprocessor"
    model = models.MeasuresBulkCreator
    template_name = "measures/cancel-bulk-processor-task.jinja"
    form_class = CancelBulkProcessorTaskForm

    def test_func(self) -> bool:
        """Method override used by UserPassesTestMixin to ensure this view's
        cancel behaviour is only available to superusers."""

        return self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "cancel-bulk-processor-task-done",
            kwargs={"pk": self.object.pk},
        )

    def get_context_data(self, **kwargs) -> Dict:
        context = super().get_context_data(**kwargs)

        context["object"] = self.object
        context["datetime_format"] = settings.DATETIME_FORMAT

        return context

    def form_valid(self, form):
        self.object.cancel_task()
        return redirect(self.get_success_url())


class CancelBulkProcessorTaskDone(
    UserPassesTestMixin,
    DetailView,
):
    """Confirm attempt to cancel a bulk processor task."""

    model = models.MeasuresBulkCreator
    template_name = "measures/cancel-bulk-processor-task-done.jinja"

    def test_func(self) -> bool:
        """Method override used by UserPassesTestMixin to ensure this view's
        cancel behaviour is only available to superusers."""

        return self.request.user.is_superuser


class MeasuresCreateProcessQueue(
    PermissionRequiredMixin,
    WithPaginationListView,
):
    """UI endpoint for bulk creating Measures process queue."""

    permission_required = [
        "common.add_trackedmodel",
        "common.change_trackedmodel",
    ]
    template_name = "measures/create-process-queue.jinja"
    model = models.MeasuresBulkCreator
    queryset = models.MeasuresBulkCreator.objects.filter(
        workbasket__status=WorkflowStatus.EDITING,
    ).order_by("-created_at")
    filterset_class = MeasureCreateTaskFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["selected_link"] = "all"
        context["selected_tab"] = "measure-process-queue"
        processing_state = self.request.GET.get("processing_state")

        if processing_state == "PROCESSING":
            context["selected_link"] = "processing"
        elif processing_state == ProcessingState.CANCELLED:
            context["selected_link"] = "terminated"
        elif processing_state == ProcessingState.FAILED_PROCESSING:
            context["selected_link"] = "failed"
        elif processing_state == ProcessingState.SUCCESSFULLY_PROCESSED:
            context["selected_link"] = "completed"
        # Provide template access to some UI / view utility functions.
        context["status_tag_generator"] = self.status_tag_generator
        context["can_terminate_task"] = self.can_terminate_task
        context["is_task_failed"] = self.is_task_failed
        context["is_task_terminated"] = self.is_task_terminated
        # Apply the TAP standard date format within the UI.
        context["datetime_format"] = settings.DATETIME_FORMAT
        if context["selected_link"] == "processing":
            context["object_list"] = self.get_processing_queryset()
        return context

    def get_processing_queryset(self):
        """Returns a combined queryset of tasks either AWAITING_PROCESSING or
        CURRENTLY_PROCESSING."""

        return self.queryset.filter(
            Q(processing_state=ProcessingState.AWAITING_PROCESSING)
            | Q(processing_state=ProcessingState.CURRENTLY_PROCESSING),
        )

    def is_task_failed(self, task: models.MeasuresBulkCreator) -> bool:
        """
        Return True if the task is in a failed state.

        Return False otherwise.
        """

        return task.processing_state == ProcessingState.FAILED_PROCESSING

    def is_task_terminated(self, task: MeasuresBulkCreator) -> bool:
        """
        Return True if the task is in a cancelled state. Cancelled tasks are
        surfaced as 'terminated' in the UI.

        Return False otherwise.
        """

        return task.processing_state == ProcessingState.CANCELLED

    def can_terminate_task(self, task: MeasuresBulkCreator) -> bool:
        """
        Return True if a task is in a queued state and the current user is
        permitted to terminate a task.

        Return False otherwise.
        """

        if (
            self.request.user.is_superuser
            and task.processing_state in ProcessingState.queued_states()
        ):
            return True

        return False

    def status_tag_generator(self, task: models.MeasuresBulkCreator) -> dict:
        """Returns a dict with text and a CSS class for a UI-friendly label for
        a bulk creation task."""

        if task.processing_state in [
            ProcessingState.CURRENTLY_PROCESSING,
            ProcessingState.AWAITING_PROCESSING,
        ]:
            return {
                "text": "Processing",
                "tag_class": "tamato-badge-light-blue",
            }
        elif task.processing_state == ProcessingState.SUCCESSFULLY_PROCESSED:
            return {
                "text": "Completed",
                "tag_class": "tamato-badge-light-green",
            }
        elif task.processing_state == ProcessingState.FAILED_PROCESSING:
            return {
                "text": "Failed",
                "tag_class": "tamato-badge-light-red",
            }
        elif task.processing_state == ProcessingState.CANCELLED:
            return {
                "text": "Terminated",
                "tag_class": "tamato-badge-light-yellow",
            }
        else:
            return {
                "text": "",
                "tag_class": "",
            }
