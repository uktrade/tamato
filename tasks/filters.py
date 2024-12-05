from django.db.models import TextChoices
from django.forms import CheckboxSelectMultiple
from django.urls import reverse_lazy
from django_filters import ChoiceFilter
from django_filters import ModelMultipleChoiceFilter

from common.filters import TamatoFilter
from common.widgets import RadioSelect
from tasks.models import ProgressState
from tasks.models import Task


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
        "id",
        "title",
        "description",
    )
    clear_url = reverse_lazy("workflow:task-workflow-ui-list")

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
