import re

from django.conf import settings
from django.db.models import TextChoices
from django.forms import CheckboxSelectMultiple
from django.forms import widgets
from django.urls import reverse_lazy
from django_filters import ChoiceFilter
from django_filters import ModelChoiceFilter
from django_filters import ModelMultipleChoiceFilter

from common.filters import TamatoFilter
from common.models import User
from common.widgets import RadioSelect
from tasks.forms import TaskFilterForm
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskWorkflowTemplate


class TaskFilter(TamatoFilter):

    search_fields = (
        "id",
        "title",
        "description",
    )
    clear_url = reverse_lazy("workflow:task-ui-list")

    progress_state = ModelMultipleChoiceFilter(
        label="Status",
        help_text="Select all that apply",
        queryset=ProgressState.objects.all(),
        widget=CheckboxSelectMultiple,
    )

    class Meta:
        model = Task
        fields = ["search", "category", "progress_state"]

    @property
    def qs(self):
        return super().qs.non_workflow()


class TaskWorkflowFilter(TamatoFilter):
    search_fields = (
        "taskworkflow__id",
        "title",
        "description",
    )
    if settings.TICKET_PREFIX:
        id_search_regex = re.compile(rf"(?i)({settings.TICKET_PREFIX}?)(\d+)")

    clear_url = reverse_lazy("workflow:task-workflow-ui-list")

    progress_state = ModelMultipleChoiceFilter(
        label="Status",
        help_text="Select all that apply",
        queryset=ProgressState.objects.all(),
        widget=CheckboxSelectMultiple,
    )

    work_type = ModelChoiceFilter(
        label="Work type",
        queryset=TaskWorkflowTemplate.objects.all(),
        field_name="taskworkflow__creator_template",
        widget=widgets.Select(),
    )

    assignees = ModelChoiceFilter(
        label="Assignees",
        field_name="assignees",
        queryset=User.objects.active_tms(),
    )

    def get_search_term(self, value):
        """Looks for a pattern matching a ticket ID with prefix and removes the
        ticket_prefix from the search groups."""
        value = value.strip()
        if self.id_search_regex:
            match = self.id_search_regex.search(value)
            if match:
                terms = list(match.groups())
                terms = [term for term in terms if term != settings.TICKET_PREFIX]
                terms.extend(
                    [value[: match.start()].strip(), value[match.end() :].strip()],
                )
                return " ".join(terms)
        return value

    class Meta:
        model = Task
        form = TaskFilterForm
        fields = [
            "search",
            "progress_state",
            "assignees",
        ]

    @property
    def qs(self):
        qs = super().qs
        return qs.workflow_summary()


class TasksAndWorkflowsChoices(TextChoices):
    TASKS_ONLY = "TASKS_ONLY", "Tasks only"
    WORKFLOWS_ONLY = "WORKFLOWS_ONLY", "Workflows only"


class TaskAndWorkflowFilter(TamatoFilter):
    search_fields = (
        "id",
        "title",
        "description",
    )
    clear_url = reverse_lazy("workflow:task-and-workflow-ui-list")

    tasks_and_workflows = ChoiceFilter(
        choices=TasksAndWorkflowsChoices.choices,
        method="filter_by_tasks_and_workflows",
        widget=RadioSelect,
        label="Tasks and workflows",
        empty_label="Tasks and workflows",
        help_text="Select the choice that applies",
    )

    progress_state = ModelMultipleChoiceFilter(
        label="Status",
        help_text="Select all that apply",
        queryset=ProgressState.objects.all(),
        widget=CheckboxSelectMultiple,
    )

    class Meta:
        model = Task
        fields = ["search", "tasks_and_workflows", "category", "progress_state"]

    def filter_by_tasks_and_workflows(self, queryset, name, value):
        if TasksAndWorkflowsChoices.TASKS_ONLY == value:
            queryset = queryset.non_workflow()
        elif TasksAndWorkflowsChoices.WORKFLOWS_ONLY == value:
            queryset = queryset.workflow_summary()

        return queryset

    @property
    def qs(self):
        return super().qs.top_level()


class WorkflowTemplateFilter(TamatoFilter):
    search_fields = (
        "id",
        "title",
        "description",
        "creator__username",
    )
    clear_url = reverse_lazy("workflow:task-workflow-template-ui-list")

    class Meta:
        model = TaskWorkflowTemplate
        fields = ["search"]
