from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django.db.models import TextChoices
from django.forms import CharField
from django.forms import Form
from django.forms import ModelChoiceField
from django.forms import ModelForm
from django.forms import Textarea

from common.forms import BindNestedFormMixin
from common.forms import RadioNested
from common.forms import delete_form_for
from common.validators import SymbolValidator
from tasks.models import Task
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
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


class TaskUpdateForm(TaskBaseForm):
    pass


class SubTaskCreateForm(TaskBaseForm):
    def save(self, parent_task, user, commit=True):
        instance = super().save(commit=False)
        instance.creator = user
        instance.parent_task = parent_task
        if commit:
            instance.save()
        return instance


TaskDeleteForm = delete_form_for(Task)


class TaskWorkflowTemplateForm(Form):
    workflow_template = ModelChoiceField(
        label="",
        queryset=TaskWorkflowTemplate.objects.all(),
        help_text="Select a workflow template.",
        error_messages={
            "required": "Select a workflow template",
        },
    )


class TaskWorkflowCreateForm(BindNestedFormMixin, Form):
    class CreateType(TextChoices):
        WITH_TEMPLATE = "WITH_TEMPLATE", "Yes"
        WITHOUT_TEMPLATE = "WITHOUT_TEMPLATE", "No"

    title = CharField(
        max_length=255,
        validators=[SymbolValidator],
        error_messages={
            "required": "Enter a title for the workflow",
        },
    )

    description = CharField(
        validators=[SymbolValidator],
        widget=Textarea(),
        error_messages={
            "required": "Enter a description for the workflow",
        },
    )

    create_type = RadioNested(
        label="Do you want to use a workflow template?",
        choices=CreateType.choices,
        nested_forms={
            CreateType.WITH_TEMPLATE.value: [TaskWorkflowTemplateForm],
            CreateType.WITHOUT_TEMPLATE.value: [],
        },
        error_messages={
            "required": "Select if you want to use a workflow template",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bind_nested_forms(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "title",
                "description",
            ),
            "create_type",
            Submit(
                "submit",
                "Create",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


TaskWorkflowDeleteForm = delete_form_for(TaskWorkflow)


class TaskWorkflowTemplateBaseForm(ModelForm):
    class Meta:
        model = TaskWorkflowTemplate
        fields = ("title", "description")

        error_messages = {
            "title": {
                "required": "Enter a title",
            },
            "description": {
                "required": "Enter a description",
            },
        }

    def __init__(self, *args, submit_title, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            Submit(
                "submit",
                submit_title,
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class TaskWorkflowTemplateCreateForm(TaskWorkflowTemplateBaseForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, submit_title="Create", **kwargs)

    def save(self, user, commit=True):
        instance = super().save(commit=False)
        instance.creator = user
        if commit:
            instance.save()
        return instance


class TaskWorkflowTemplateUpdateForm(TaskWorkflowTemplateBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, submit_title="Update", **kwargs)


TaskWorkflowTemplateDeleteForm = delete_form_for(TaskWorkflowTemplate)


class TaskTemplateFormBase(ModelForm):
    class Meta:
        model = TaskTemplate
        fields = ("title", "description")

    def __init__(self, *args, submit_title, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            Submit(
                "submit",
                submit_title,
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class TaskTemplateCreateForm(TaskTemplateFormBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, submit_title="Create", **kwargs)


class TaskTemplateUpdateForm(TaskTemplateFormBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, submit_title="Update", **kwargs)


TaskTemplateDeleteForm = delete_form_for(TaskTemplate)
