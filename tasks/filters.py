import re

from django.conf import settings
from django.db.models import Q
from django.db.models import TextChoices
from django.forms import CheckboxSelectMultiple
from django.forms import widgets
from django.urls import reverse_lazy
from django_filters import ChoiceFilter
from django_filters import ModelChoiceFilter
from django_filters import ModelMultipleChoiceFilter
from django_filters import MultipleChoiceFilter

from common.filters import TamatoFilter
from common.models import User
from common.widgets import RadioSelect
from tasks.forms import TaskFilterForm
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
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


class TaskWorkflowAssignmentChoices(TextChoices):
    ASSIGNED = "assigned", "Assigned"
    NOT_ASSIGNED = "not_assigned", "Not assigned"


class TaskWorkflowFilter(TamatoFilter):
    search_fields = (
        "taskworkflow__id",
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

    work_type = ModelChoiceFilter(
        label="Work type",
        queryset=TaskWorkflowTemplate.objects.all(),
        field_name="taskworkflow__creator_template",
        widget=widgets.Select(),
    )

    assignees = ModelChoiceFilter(
        label="Assignees",
        method="filter_by_current_assignee",
        queryset=User.objects.active_tms(),
    )

    assignment_status = MultipleChoiceFilter(
        choices=TaskWorkflowAssignmentChoices.choices,
        method="filter_by_assignment_status",
        label="Assignment status",
        widget=CheckboxSelectMultiple,
    )

    class Meta:
        model = Task
        form = TaskFilterForm
        fields = [
            "search",
            "progress_state",
            "assignees__user",
            "assignment_status",
        ]

    def get_search_term(self, value):
        return self.normalise_prefixed_ticket_ids(value)

    def normalise_prefixed_ticket_ids(self, search_sentence: str) -> str:
        """
        Normalise all terms in `search_sentence` that match prefixed ticket IDs
        and return the normalised result.

        Ticket IDs may be 'bare' (no prefix included) or include the ticket ID
        prefix string. For instance, given a ticket ID prefix of 'TC-', then
        both 'TC-123' and '123' would be considered valid IDs.
        """

        if not settings.TICKET_PREFIX or not search_sentence.strip():
            return search_sentence

        normalised_tokens = []

        for token in search_sentence.strip().split(" "):
            match = re.match(
                pattern=rf"({settings.TICKET_PREFIX})(\d+)",
                string=token,
                flags=re.IGNORECASE,
            )

            if match:
                normalised_tokens.append(match[2])
            else:
                normalised_tokens.append(token)

        return " ".join(normalised_tokens)

    def filter_by_assignment_status(self, queryset, name, value):
        assignment_status = Q()

        if TaskWorkflowAssignmentChoices.ASSIGNED in value:
            assigned_tasks = TaskAssignee.objects.assigned().values_list(
                "task__id",
                flat=True,
            )
            assignment_status |= Q(id__in=assigned_tasks)

        if TaskWorkflowAssignmentChoices.NOT_ASSIGNED in value:
            never_assigned = Task.objects.not_assigned_workflow().values_list(
                "id",
                flat=True,
            )

            unassigned_tasks = (
                TaskAssignee.objects.unassigned()
                .distinct()
                .values_list(
                    "task__id",
                    flat=True,
                )
            )

            assigned_tasks = (
                TaskAssignee.objects.assigned()
                .distinct()
                .values_list(
                    "task__id",
                    flat=True,
                )
            )

            unassigned_or_never = set(list(unassigned_tasks) + list(never_assigned))

            assignment_status |= Q(
                Q(id__in=unassigned_or_never),
                ~Q(id__in=assigned_tasks),
            )

        return queryset.filter(assignment_status)

    def filter_by_current_assignee(self, queryset, name, value):
        active_assigned_tasks = (
            TaskAssignee.objects.assigned()
            .filter(user=value)
            .distinct()
            .values_list(
                "task__id",
                flat=True,
            )
        )
        return queryset.filter(id__in=active_assigned_tasks)

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
