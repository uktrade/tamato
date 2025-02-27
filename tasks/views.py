from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
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
from django.views.generic.edit import FormView
from django.views.generic.edit import UpdateView

from common.views import SortingMixin
from common.views import WithPaginationListView
from tasks.filters import TaskAndWorkflowFilter
from tasks.filters import TaskFilter
from tasks.filters import TaskWorkflowFilter
from tasks.filters import WorkflowTemplateFilter
from tasks.forms import AssignUsersForm
from tasks.forms import SubTaskCreateForm
from tasks.forms import TaskCreateForm
from tasks.forms import TaskDeleteForm
from tasks.forms import TaskTemplateCreateForm
from tasks.forms import TaskTemplateDeleteForm
from tasks.forms import TaskTemplateUpdateForm
from tasks.forms import TaskUpdateForm
from tasks.forms import TaskWorkflowCreateForm
from tasks.forms import TaskWorkflowDeleteForm
from tasks.forms import TaskWorkflowTemplateCreateForm
from tasks.forms import TaskWorkflowTemplateDeleteForm
from tasks.forms import TaskWorkflowTemplateUpdateForm
from tasks.forms import TaskWorkflowUpdateForm
from tasks.forms import UnassignUsersForm
from tasks.models import Queue
from tasks.models import QueueItem
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskItem
from tasks.models import TaskItemTemplate
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
from tasks.signals import set_current_instigator

User = get_user_model()


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

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        return context


class TaskDetailView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/detail.jinja"
    permission_required = "tasks.view_task"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        # TODO: Factor out queries and place in TaskAssigeeQuerySet.
        current_assignees = TaskAssignee.objects.filter(
            task=self.get_object(),
            # TODO:
            # Using all task assignees is temporary for illustration as it
            # doesn't align with the new approach of assigning users to tasks
            # rather than assigning users to workbaskets (the old approach,
            # uses tasks as an intermediary joining object).
            # assignment_type=TaskAssignee.AssignmentType.GENERAL,
        ).assigned()

        context["current_assignees"] = [
            {"pk": assignee.pk, "name": assignee.user.get_full_name()}
            for assignee in current_assignees.order_by(
                "user__first_name",
                "user__last_name",
            )
        ]
        context["assignable_users"] = [
            {"pk": user.pk, "name": user.get_full_name()}
            for user in User.objects.active_tms().exclude(
                pk__in=current_assignees.values_list("user__pk", flat=True),
            )
        ]

        return context


class TaskCreateView(PermissionRequiredMixin, CreateView):
    model = Task
    template_name = "tasks/create.jinja"
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit task details"
        return context

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Task updated"
        context["object_type"] = "Task"
        return context


class TaskDeleteView(PermissionRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/delete.jinja"
    permission_required = "tasks.delete_task"
    form_class = TaskDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["verbose_name"] = "task"
        return context_data

    def get_success_url(self):
        return reverse("workflow:task-ui-confirm-delete", kwargs={"pk": self.object.pk})


class TaskConfirmDeleteView(PermissionRequiredMixin, TemplateView):
    model = Task
    template_name = "tasks/confirm_delete.jinja"
    permission_required = "tasks.delete_task"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["deleted_pk"] = self.kwargs["pk"]
        context_data["verbose_name"] = "task"
        return context_data


class TaskAssignUsersView(PermissionRequiredMixin, FormView):
    permission_required = "tasks.add_taskassignee"
    template_name = "tasks/assign_users.jinja"
    form_class = AssignUsersForm

    @property
    def task(self):
        return Task.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Assign users to task"
        return context

    def form_valid(self, form):
        form.assign_users(task=self.task, user_instigator=self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "workflow:task-ui-detail",
            kwargs={"pk": self.kwargs["pk"]},
        )


class TaskUnassignUsersView(PermissionRequiredMixin, FormView):
    permission_required = "tasks.change_taskassignee"
    template_name = "tasks/assign_users.jinja"
    form_class = UnassignUsersForm

    @property
    def task(self):
        return Task.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Unassign users from task"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["task"] = self.task
        return kwargs

    def form_valid(self, form):
        form.unassign_users(self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "workflow:task-ui-detail",
            kwargs={"pk": self.kwargs["pk"]},
        )


class SubTaskCreateView(PermissionRequiredMixin, CreateView):
    model = Task
    template_name = "tasks/create.jinja"
    permission_required = "tasks.add_task"
    form_class = SubTaskCreateForm

    @property
    def parent_task(self) -> Task:
        return Task.objects.get(pk=self.kwargs["parent_task_pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = (
            f"Create a subtask for task {self.kwargs['parent_task_pk']}"
        )
        context["parent_task"] = self.parent_task
        return context

    def form_valid(self, form):
        if self.parent_task.parent_task:
            form.add_error(
                None,
                "You cannot make a subtask from a subtask.",
            )
            return self.form_invalid(form)
        else:
            self.object = form.save(self.parent_task, user=self.request.user)
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


class SubTaskUpdateView(PermissionRequiredMixin, UpdateView):
    model = Task
    template_name = "tasks/edit.jinja"
    permission_required = "tasks.change_task"
    form_class = TaskUpdateForm

    def form_valid(self, form):
        set_current_instigator(self.request.user)
        with transaction.atomic():
            self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit subtask {self.object.pk}"
        return context

    def get_success_url(self):
        return reverse(
            "workflow:subtask-ui-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class SubTaskConfirmUpdateView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/confirm_update.jinja"
    permission_required = "tasks.change_task"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Subtask updated"
        context["object_type"] = "Subtask"
        return context


class SubTaskDeleteView(PermissionRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/delete.jinja"
    permission_required = "tasks.delete_task"
    form_class = TaskDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["verbose_name"] = "subtask"
        return context_data

    def get_success_url(self):
        return reverse(
            "workflow:subtask-ui-confirm-delete",
            kwargs={"pk": self.object.pk},
        )


class SubTaskConfirmDeleteView(PermissionRequiredMixin, TemplateView):
    model = Task
    template_name = "tasks/confirm_delete.jinja"
    permission_required = "tasks.delete_task"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["verbose_name"] = "subtask"
        context_data["deleted_pk"] = self.kwargs["pk"]
        return context_data


class TaskWorkflowListView(
    PermissionRequiredMixin,
    SortingMixin,
    WithPaginationListView,
):
    model = Task
    template_name = "tasks/workflows/list.jinja"
    permission_required = "tasks.view_task"
    paginate_by = settings.DEFAULT_PAGINATOR_PER_PAGE_MAX
    filterset_class = TaskWorkflowFilter
    sort_by_fields = ["created_at"]

    def get_queryset(self):
        queryset = Task.objects.all()
        ordering = self.get_ordering()
        if ordering:
            ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        return context


class TaskAndWorkflowListView(
    PermissionRequiredMixin,
    SortingMixin,
    WithPaginationListView,
):
    model = Task
    template_name = "tasks/workflows/task-and-workflow-list.jinja"
    permission_required = "tasks.view_task"
    paginate_by = settings.DEFAULT_PAGINATOR_PER_PAGE_MAX
    filterset_class = TaskAndWorkflowFilter
    sort_by_fields = ["created_at"]

    def get_queryset(self):
        queryset = Task.objects.all()
        ordering = self.get_ordering()
        if ordering:
            ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        return context


class TaskWorkflowTemplateListView(
    PermissionRequiredMixin,
    SortingMixin,
    WithPaginationListView,
):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/template_list.jinja"
    permission_required = "tasks.view_taskworkflowtemplate"
    paginate_by = 20
    filterset_class = WorkflowTemplateFilter
    sort_by_fields = ["created_at", "updated_at"]

    def get_context_data(self, **kwargs) -> dict:
        context_data = super().get_context_data(**kwargs)
        context_data["datetime_format"] = settings.DATETIME_FORMAT
        return context_data

    def get_queryset(self):
        queryset = TaskWorkflowTemplate.objects.all()
        ordering = self.get_ordering()
        if ordering:
            ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset


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


class TaskWorkflowDetailView(
    PermissionRequiredMixin,
    QueuedItemManagementMixin,
    DetailView,
):
    template_name = "tasks/workflows/detail.jinja"
    permission_required = "tasks.view_taskworkflow"
    model = TaskWorkflow
    queued_item_model = TaskItem
    item_lookup_field = "task_id"
    queue_field = queued_item_model.queue_field

    @property
    def view_url(self) -> str:
        return reverse(
            "workflow:task-workflow-ui-detail",
            kwargs={"pk": self.queue.pk},
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["object_list"] = self.queue.get_tasks()
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


class TaskWorkflowCreateView(PermissionRequiredMixin, FormView):
    permission_required = "tasks.add_taskworkflow"
    template_name = "tasks/workflows/create.jinja"
    form_class = TaskWorkflowCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = "workflow"
        context["list_url"] = "#NOT-IMPLEMENTED"
        return context

    def form_valid(self, form):
        summary_data = {
            "title": form.cleaned_data["title"],
            "description": form.cleaned_data["description"],
            "creator": self.request.user,
        }
        create_type = form.cleaned_data["create_type"]

        if create_type == TaskWorkflowCreateForm.CreateType.WITH_TEMPLATE:
            template = form.cleaned_data["workflow_template"]
            self.object = template.create_task_workflow(**summary_data)
        elif create_type == TaskWorkflowCreateForm.CreateType.WITHOUT_TEMPLATE:
            with transaction.atomic():
                summary_task = Task.objects.create(**summary_data)
                self.object = TaskWorkflow.objects.create(
                    summary_task=summary_task,
                )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-ui-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowConfirmCreateView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflow
    template_name = "tasks/workflows/confirm_create.jinja"
    permission_required = "tasks.add_taskworkflow"


class TaskWorkflowUpdateView(PermissionRequiredMixin, UpdateView):
    model = TaskWorkflow
    template_name = "tasks/workflows/edit.jinja"
    permission_required = "tasks.change_taskworkflow"
    form_class = TaskWorkflowUpdateForm

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-ui-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowConfirmUpdateView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflow
    template_name = "tasks/workflows/confirm_update.jinja"
    permission_required = "tasks.change_taskworkflow"


class TaskWorkflowDeleteView(PermissionRequiredMixin, DeleteView):
    model = TaskWorkflow
    template_name = "tasks/workflows/delete.jinja"
    permission_required = "tasks.delete_taskworkflow"
    form_class = TaskWorkflowDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["verbose_name"] = "ticket"
        return context_data

    @transaction.atomic
    def form_valid(self, form):
        summary_task = self.object.summary_task
        self.object.get_tasks().delete()
        result = super().form_valid(form)
        summary_task.delete()
        return result

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-ui-confirm-delete",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowConfirmDeleteView(PermissionRequiredMixin, TemplateView):
    model = TaskWorkflow
    template_name = "tasks/workflows/confirm_delete.jinja"
    permission_required = "tasks.change_taskworkflow"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data.update(
            {
                "verbose_name": "workflow",
                "deleted_pk": self.kwargs["pk"],
                "create_url": reverse("workflow:task-workflow-ui-create"),
                "list_url": "#NOT-IMPLEMENTED",
            },
        )
        return context_data


class TaskWorkflowTaskCreateView(PermissionRequiredMixin, CreateView):
    model = Task
    template_name = "layouts/create.jinja"
    permission_required = "tasks.add_task"
    form_class = TaskCreateForm

    def get_task_workflow(self):
        """Get the associated TaskWorkflow via its pk in the URL."""
        return TaskWorkflow.objects.get(
            pk=self.kwargs["task_workflow_pk"],
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Create a task"
        return context

    def form_valid(self, form) -> HttpResponseRedirect:
        with transaction.atomic():
            self.object = form.save(user=self.request.user)
            TaskItem.objects.create(
                workflow=self.get_task_workflow(),
                task=self.object,
            )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-task-ui-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowTaskConfirmCreateView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/confirm_create.jinja"
    permission_required = "tasks.add_task"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = "task"
        return context


class TaskWorkflowTemplateDetailView(
    PermissionRequiredMixin,
    QueuedItemManagementMixin,
    DetailView,
):
    template_name = "tasks/workflows/detail.jinja"
    permission_required = "tasks.view_taskworkflowtemplate"
    model = TaskWorkflowTemplate
    queued_item_model = TaskItemTemplate
    item_lookup_field = "task_template_id"
    queue_field = queued_item_model.queue_field

    @property
    def view_url(self) -> str:
        return reverse(
            "workflow:task-workflow-template-ui-detail",
            kwargs={"pk": self.queue.pk},
        )

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["object_list"] = self.queue.get_task_templates()
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


class TaskWorkflowTemplateCreateView(PermissionRequiredMixin, CreateView):
    model = TaskWorkflowTemplate
    permission_required = "tasks.add_taskworkflowtemplate"
    template_name = "tasks/workflows/create.jinja"
    form_class = TaskWorkflowTemplateCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = "workflow template"
        context["list_url"] = reverse("workflow:task-workflow-template-ui-list")
        return context

    def form_valid(self, form):
        self.object = form.save(user=self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-template-ui-confirm-create",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowTemplateConfirmCreateView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/confirm_create.jinja"
    permission_required = "tasks.add_taskworkflowtemplate"


class TaskWorkflowTemplateUpdateView(PermissionRequiredMixin, UpdateView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/edit.jinja"
    permission_required = "tasks.change_taskworkflowtemplate"
    form_class = TaskWorkflowTemplateUpdateForm

    def get_success_url(self):
        return reverse(
            "workflow:task-workflow-template-ui-confirm-update",
            kwargs={"pk": self.object.pk},
        )


class TaskWorkflowTemplateConfirmUpdateView(PermissionRequiredMixin, DetailView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/confirm_update.jinja"
    permission_required = "tasks.change_taskworkflowtemplate"


class TaskWorkflowTemplateDeleteView(PermissionRequiredMixin, DeleteView):
    model = TaskWorkflowTemplate
    template_name = "tasks/workflows/delete.jinja"
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
    template_name = "tasks/workflows/confirm_delete.jinja"
    permission_required = "tasks.change_taskworkflowtemplate"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data.update(
            {
                "verbose_name": "workflow template",
                "deleted_pk": self.kwargs["pk"],
                "create_url": reverse("workflow:task-workflow-template-ui-create"),
                "list_url": reverse("workflow:task-workflow-template-ui-list"),
            },
        )
        return context_data


class TaskTemplateDetailView(PermissionRequiredMixin, DetailView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_detail.jinja"
    permission_required = "tasks.view_tasktemplate"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        context["task_workflow_template"] = (
            self.get_object().taskitemtemplate.workflow_template
        )

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
                workflow_template=self.get_task_workflow_template(),
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

        context["task_workflow_template"] = (
            self.get_object().taskitemtemplate.workflow_template
        )

        return context


class TaskTemplateUpdateView(PermissionRequiredMixin, UpdateView):
    model = TaskTemplate
    template_name = "tasks/workflows/task_template_save.jinja"
    permission_required = "tasks.change_tasktemplate"
    form_class = TaskTemplateUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = f"Update task template: {self.get_object().title}"
        context["task_workflow_template"] = (
            self.get_object().taskitemtemplate.workflow_template
        )

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

        context["task_workflow_template"] = (
            self.get_object().taskitemtemplate.workflow_template
        )

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

        context["task_workflow_template"] = (
            self.get_object().taskitemtemplate.workflow_template
        )

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
