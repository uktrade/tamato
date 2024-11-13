from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import UpdateView

from common.views import SortingMixin
from common.views import WithPaginationListView
from tasks.filters import TaskFilter
from tasks.forms import SubTaskCreateForm
from tasks.forms import TaskCreateForm
from tasks.forms import TaskDeleteForm
from tasks.forms import TaskTemplateCreateForm
from tasks.forms import TaskUpdateForm
from tasks.models import Task
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflowTemplate
from tasks.signals import set_current_instigator


class TaskListView(PermissionRequiredMixin, SortingMixin, WithPaginationListView):
    model = Task
    template_name = "tasks/list.jinja"
    permission_required = "tasks.view_task"
    paginate_by = 20
    filterset_class = TaskFilter
    sort_by_fields = ["created_at"]

    def get_queryset(self):
        queryset = Task.objects.all()
        ordering = self.get_ordering()
        if ordering:
            ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset


class TaskDetailView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/detail.jinja"
    permission_required = "tasks.view_task"


class TaskCreateView(PermissionRequiredMixin, CreateView):
    model = Task
    template_name = "layouts/create.jinja"
    permission_required = "tasks.add_task"
    form_class = TaskCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create a task"
        return context

    def form_valid(self, form):
        self.object = form.save(user=self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("workflow:task-ui-confirm-create", kwargs={"pk": self.object.pk})


class TaskConfirmCreateView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/confirm_create.jinja"
    permission_required = "tasks.add_task"


class TaskUpdateView(PermissionRequiredMixin, UpdateView):
    model = Task
    template_name = "tasks/edit.jinja"
    permission_required = "tasks.change_task"
    form_class = TaskUpdateForm

    def form_valid(self, form):
        set_current_instigator(self.request.user)
        with transaction.atomic():
            self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("workflow:task-ui-confirm-update", kwargs={"pk": self.object.pk})


class TaskConfirmUpdateView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/confirm_update.jinja"
    permission_required = "tasks.change_task"


class TaskDeleteView(PermissionRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/delete.jinja"
    permission_required = "tasks.delete_task"
    form_class = TaskDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_success_url(self):
        return reverse("workflow:task-ui-confirm-delete", kwargs={"pk": self.object.pk})


class TaskConfirmDeleteView(PermissionRequiredMixin, TemplateView):
    model = Task
    template_name = "tasks/confirm_delete.jinja"
    permission_required = "tasks.delete_task"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["pk"]
        return context_data


class SubTaskCreateView(PermissionRequiredMixin, CreateView):
    model = Task
    template_name = "layouts/create.jinja"
    permission_required = "tasks.add_task"
    form_class = SubTaskCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create a subtask"
        return context

    def form_valid(self, form):
        parent_task = Task.objects.filter(pk=self.kwargs["pk"]).first()
        self.object = form.save(parent_task, user=self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("workflow:task-ui-confirm-create", kwargs={"pk": self.object.pk})


class TaskWorkflowTemplateDetailView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_detail.jinja"
    permission_required = "tasks.view_taskworkflowtemplate"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["task_template_items"] = (
            self.get_object().get_items().select_related("task_template")
        )
        return context_data


class TaskTemplateDetailView(PermissionRequiredMixin, DetailView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_detail.jinja"
    permission_required = "tasks.view_tasktemplate"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["task_workflow_template"] = self.get_object().taskitemtemplate.queue

        return context


class TaskTemplateCreateView(PermissionRequiredMixin, CreateView):
    template_name = "tasks/workflows/task_template_create.jinja"
    form_class = TaskTemplateCreateForm
    permission_required = "tasks.add_tasktemplate"

    def get_task_workflow_template(self) -> TaskWorkflowTemplate:
        """Get the TaskWorkflowTemplate identified by the pk in the URL."""
        return TaskWorkflowTemplate.objects.get(
            pk=self.kwargs["workflow_template_pk"],
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["task_workflow_template"] = self.get_task_workflow_template()

        return context

    def form_valid(self, form) -> HttpResponseRedirect:
        with transaction.atomic():
            self.object = form.save()
            TaskItemTemplate.objects.create(
                queue=self.get_task_workflow_template(),
                task_template=self.object,
            )

        return HttpResponseRedirect(self.get_success_url(), self.object.pk)

    def get_success_url(self) -> str:
        return reverse(
            "workflow:task-template-ui-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class TaskTemplateConfirmCreateView(PermissionRequiredMixin, DetailView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_confirm_create.jinja"
    permission_required = "tasks.add_tasktemplate"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["task_workflow_template"] = self.get_object().taskitemtemplate.queue

        return context
