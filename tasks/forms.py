from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django.forms import ModelForm

from tasks.models import Task
from workbaskets.models import WorkBasket


class TaskBaseForm(ModelForm):
    class Meta:
        model = Task
        exclude = ["parent_task", "creator"]

        error_messages = {
            "title": {
                "required": "Enter a title",
            },
            "description": {
                "required": "Enter a description",
            },
            "progress_state": {
                "required": "Select a status",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["progress_state"].label = "Status"
        self.fields["workbasket"].queryset = WorkBasket.objects.editable()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            "category",
            "progress_state",
            "workbasket",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class TaskCreateForm(TaskBaseForm):
    def save(self, user, commit=True):
        instance = super().save(commit=False)
        instance.creator = user
        if commit:
            instance.save()
        return instance
