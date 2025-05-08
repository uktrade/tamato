import logging

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.transaction import atomic
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from tasks.models import Task
from workbaskets.forms import AutomationCreateWorkBasketForm
from workbaskets.models import CreateWorkBasketAutomation

logger = logging.getLogger(__name__)


class AutomationCreateWorkBasketView(PermissionRequiredMixin, FormView):
    """UI endpoint for automated task workbasket creation."""

    permission_required = "workbaskets.add_workbasket"
    template_name = "workbaskets/task_automation/create_workbasket.jinja"
    form_class = AutomationCreateWorkBasketForm

    def get_automation(self) -> CreateWorkBasketAutomation:
        """Return the CreateWorkBasketAutomation instance that this view
        runs."""
        return CreateWorkBasketAutomation.objects.get(pk=self.kwargs["pk"])

    @property
    def task(self) -> Task:
        """Return the Task instance associated with the automation."""
        return self.get_automation().task

    def get_success_url(self):
        return reverse("workflow:task-ui-detail", kwargs={"pk": self.task.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["automation"] = self.get_automation()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        workflow = self.task.get_workflow()
        context["ticket_title"] = workflow.title
        context["ticket_prefixed_id"] = workflow.prefixed_id
        context["ticket_id"] = workflow.id
        context["step_title"] = f"Step: {self.task.title}"
        context["step_id"] = self.task.id
        context["page_title"] = "Create a workbasket"

        return context

    @atomic
    def form_valid(self, form):
        automation = self.get_automation()
        automation.run_automation(user=self.request.user)
        self.task.get_workflow().summary_task.workbasket.set_as_current(
            self.request.user,
        )

        return redirect(self.get_success_url())
