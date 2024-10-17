from django.forms import CheckboxSelectMultiple
from django.urls import reverse_lazy
from django_filters import ModelMultipleChoiceFilter

from common.filters import TamatoFilter
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
