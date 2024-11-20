from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
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
from tasks.forms import TaskTemplateDeleteForm
from tasks.forms import TaskTemplateUpdateForm
from tasks.forms import TaskUpdateForm
from tasks.forms import TaskWorkflowTemplateCreateForm
from tasks.forms import TaskWorkflowTemplateDeleteForm
from tasks.forms import TaskWorkflowTemplateUpdateForm
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = "task"
        return context


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
        context["page_title"] = f"Create a subtask for task {self.kwargs['pk']}"
        return context

    def form_valid(self, form):
        self.object = form.save(
            parent_task=Task.objects.get(pk=self.kwargs["pk"]),
            user=self.request.user,
            commit=False,
        )

        try:
            self.object.full_clean()
        except ValidationError as error:
            for message in error.messages:
                form.add_error(field=None, error=message)
            return self.form_invalid(form)

        self.objectj.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "workflow:subtask-ui-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class SubTaskConfirmCreateView(DetailView):
    model = Task
    template_name = "tasks/confirm_create.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = "subtask"
        return context


class TaskWorkflowTemplateDetailView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_detail.jinja"
    permission_required = "tasks.view_taskworkflowtemplate"

    @cached_property
    def task_workflow_template(self) -> TaskWorkflowTemplate:
        return self.get_object()

    @property
    def view_url(self) -> str:
        return reverse(
            "workflow:task-workflow-template-ui-detail",
            kwargs={"pk": self.task_workflow_template.pk},
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["object_list"] = self.task_workflow_template.get_task_templates()
        return context_data

    def post(self, request, *args, **kwargs):
        if "promote" in request.POST:
            self.promote(request.POST.get("promote"))
        elif "demote" in request.POST:
            self.demote(request.POST.get("demote"))
        elif "promote_to_first" in request.POST:
            self.promote_to_first(request.POST.get("promote_to_first"))
        elif "demote_to_last" in request.POST:
            self.demote_to_last(request.POST.get("demote_to_last"))

        return HttpResponseRedirect(self.view_url)

    def promote(self, task_template_id: int) -> None:
        task_item_template = get_object_or_404(
            TaskItemTemplate,
            task_template_id=task_template_id,
            queue=self.task_workflow_template,
        )
        try:
            task_item_template.promote()
        except OperationalError:
            pass

    def demote(self, task_template_id: int) -> None:
        task_item_template = get_object_or_404(
            TaskItemTemplate,
            task_template_id=task_template_id,
            queue=self.task_workflow_template,
        )
        try:
            task_item_template.demote()
        except OperationalError:
            pass

    def promote_to_first(self, task_template_id: int) -> None:
        task_item_template = get_object_or_404(
            TaskItemTemplate,
            task_template_id=task_template_id,
            queue=self.task_workflow_template,
        )
        try:
            task_item_template.promote_to_first()
        except OperationalError:
            pass

    def demote_to_last(self, task_template_id: int) -> None:
        task_item_template = get_object_or_404(
            TaskItemTemplate,
            task_template_id=task_template_id,
            queue=self.task_workflow_template,
        )
        try:
            task_item_template.demote_to_last()
        except OperationalError:
            pass


class TaskWorkflowTemplateCreateView(PermissionRequiredMixin, CreateView):
    model = TaskWorkflowTemplate
    permission_required = "tasks.add_taskworkflowtemplate"
    template_name = "tasks/workflows/template_create.jinja"
    form_class = TaskWorkflowTemplateCreateForm

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-template-ui-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowTemplateConfirmCreateView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_confirm_create.jinja"
    permission_required = "tasks.add_taskworkflowtemplate"


class TaskWorkflowTemplateUpdateView(PermissionRequiredMixin, UpdateView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_edit.jinja"
    permission_required = "tasks.change_taskworkflowtemplate"
    form_class = TaskWorkflowTemplateUpdateForm

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-template-ui-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowTemplateConfirmUpdateView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_confirm_update.jinja"
    permission_required = "tasks.change_taskworkflowtemplate"


class TaskWorkflowTemplateDeleteView(PermissionRequiredMixin, DeleteView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_delete.jinja"
    permission_required = "tasks.delete_taskworkflowtemplate"
    form_class = TaskWorkflowTemplateDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        self.object.get_task_templates().delete()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-template-ui-confirm-delete",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowTemplateConfirmDeleteView(PermissionRequiredMixin, TemplateView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_confirm_delete.jinja"
    permission_required = "tasks.change_taskworkflowtemplate"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["pk"]
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
    template_name = "tasks/workflows/task_template_save.jinja"
    form_class = TaskTemplateCreateForm
    permission_required = "tasks.add_tasktemplate"

    def get_task_workflow_template(self) -> TaskWorkflowTemplate:
        """Get the TaskWorkflowTemplate identified by the pk in the URL."""
        return TaskWorkflowTemplate.objects.get(
            pk=self.kwargs["workflow_template_pk"],
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Create a task template"
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


class TaskTemplateUpdateView(PermissionRequiredMixin, UpdateView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_save.jinja"
    permission_required = "tasks.change_tasktemplate"
    form_class = TaskTemplateUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = f"Update task template: {self.get_object().title}"
        context["task_workflow_template"] = self.get_object().taskitemtemplate.queue

        return context

    def get_success_url(self):
        return reverse(
            "workflow:task-template-ui-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class TaskTemplateConfirmUpdateView(PermissionRequiredMixin, DetailView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_confirm_update.jinja"
    permission_required = "tasks.add_tasktemplate"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["task_workflow_template"] = self.get_object().taskitemtemplate.queue

        return context


class TaskTemplateDeleteView(PermissionRequiredMixin, DeleteView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_delete.jinja"
    permission_required = "tasks.delete_tasktemplate"
    form_class = TaskTemplateDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["task_workflow_template"] = self.get_object().taskitemtemplate.queue

        return context

    def get_success_url(self):
        return reverse(
            "workflow:task-template-ui-confirm-delete",
            kwargs={
                "workflow_template_pk": self.kwargs["workflow_template_pk"],
                "pk": self.object.pk,
            },
        )


class TaskTemplateConfirmDeleteView(PermissionRequiredMixin, TemplateView):
    template_name = "tasks/workflows/task_template_confirm_delete.jinja"
    permission_required = "tasks.delete_tasktemplate"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["deleted_pk"] = self.kwargs["pk"]
        context["task_workflow_template"] = TaskWorkflowTemplate.objects.get(
            pk=self.kwargs["workflow_template_pk"],
        )

        return context
