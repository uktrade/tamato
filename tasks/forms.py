import bleach
import markdown
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import TextChoices
from django.forms import CharField
from django.forms import ChoiceField
from django.forms import Form
from django.forms import ModelChoiceField
from django.forms import ModelForm
from django.forms import Textarea
from django.urls import reverse

from common.fields import AutoCompleteField
from common.forms import BindNestedFormMixin
from common.forms import DateInputFieldFixed
from common.forms import RadioNested
from common.forms import delete_form_for
from common.validators import SymbolValidator
from common.validators import markdown_tags_allowlist
from tasks.models import Comment
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
from workbaskets.models import WorkBasket

User = get_user_model()


class TaskCreateForm(ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "category",
            "workbasket",
        ]

        error_messages = {
            "title": {
                "required": "Enter a title",
            },
            "description": {
                "required": "Enter a description",
            },
        }

    workbasket = AutoCompleteField(
        label="Workbasket",
        help_text=(
            "Search for a workbasket by typing in the workbasket's ID, TOPS/Jira number or description. "
            "A dropdown list will appear after a few seconds. You can then select the correct workbasket from the dropdown list."
        ),
        queryset=WorkBasket.objects.editable(),
        url_pattern_name="workbaskets:workbasket-autocomplete-list",
        attrs={"min_length": 2},
        error_messages={
            "invalid_choice": "Select a workbasket that is in the editing state",
        },
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            "category",
            "workbasket",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def save(self, user, commit=True):
        instance = super().save(commit=False)
        instance.creator = user
        if commit:
            instance.save()
        return instance


class TaskUpdateForm(Form):
    progress_state = ChoiceField(
        label="Status",
        choices=ProgressState.choices,
        error_messages={"required": "Select a state"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "progress_state",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def update_status(self, task) -> bool:
        new_status = self.cleaned_data["progress_state"]
        if task.progress_state != new_status:
            match new_status:
                case ProgressState.TO_DO:
                    task.to_do()
                case ProgressState.IN_PROGRESS:
                    task.in_progress()
                case ProgressState.DONE:
                    task.done()
        else:
            raise ValidationError(
                {
                    "progress_state": "The selected option is not permitted.",
                },
            )
        return task


class AssignUserForm(Form):
    user = ModelChoiceField(
        label="Select user",
        queryset=User.objects.active_tms(),
        error_messages={"required": "Select a user to assign"},
    )

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task", None)
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["user"].label_from_instance = lambda obj: obj.get_displayname()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "user",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        if self.task.assignees.assigned().exists():
            raise ValidationError(
                {
                    "user": "The selected user cannot be assigned because the step already has an assignee.",
                },
            )

        return super().clean()

    @transaction.atomic
    def assign_user(self, task: Task, user_instigator) -> TaskAssignee:
        user = self.cleaned_data["user"]

        return TaskAssignee.assign_user(
            user=user,
            task=task,
            instigator=user_instigator,
        )


class UnassignUserForm(Form):
    assignee = ModelChoiceField(
        label="Select user",
        queryset=TaskAssignee.objects.assigned(),
        error_messages={"required": "Select a user to unassign"},
    )

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task", None)
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["assignee"].queryset = self.task.assignees.assigned()
        self.fields["assignee"].label_from_instance = (
            lambda obj: obj.user.get_displayname()
        )

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "assignee",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        if self.task.progress_state == ProgressState.DONE:
            raise ValidationError(
                {
                    "assignee": "The selected user cannot be unassigned because the step has a status of Done.",
                },
            )

        return super().clean()

    @transaction.atomic
    def unassign_user(self, user_instigator) -> bool:
        assignee = self.cleaned_data["assignee"]

        return TaskAssignee.unassign_user(
            user=assignee.user,
            task=self.task,
            instigator=user_instigator,
        )


class SubTaskCreateForm(TaskCreateForm):
    def save(self, parent_task, user, commit=True):
        instance = super().save(user=user, commit=False)
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


class TaskWorkflowAssigneeForm(Form):
    assignee = ModelChoiceField(
        queryset=User.objects.active_tms(),
        help_text="Choose assignee",
        error_messages={
            "required": "Select an assignee",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].label_from_instance = lambda obj: obj.get_displayname()


class TaskWorkflowCreateForm(BindNestedFormMixin, Form):
    class AssignType(TextChoices):
        SELF = "SELF", "Assign ticket to me"
        OTHER_USER = "OTHER_USER", "Assign ticket to someone else"
        NO_USER = "NO_USER", "Do not assign ticket to anyone"

    ticket_name = CharField(
        required=True,
        max_length=255,
        validators=[SymbolValidator],
        error_messages={
            "required": "Enter a title for the ticket",
        },
    )

    work_type = ModelChoiceField(
        required=True,
        help_text="Choose the most appropriate category. This will generate a pre-defined set of steps to complete the work",
        queryset=TaskWorkflowTemplate.objects.all(),
        error_messages={
            "required": "Choose a work type",
        },
    )

    assignment = RadioNested(
        label="Assignee",
        choices=AssignType.choices,
        nested_forms={
            AssignType.SELF.value: [],
            AssignType.OTHER_USER: [TaskWorkflowAssigneeForm],
            AssignType.NO_USER.value: [],
        },
        error_messages={
            "required": "Select an assignee option",
        },
    )

    description = CharField(
        required=False,
        validators=[SymbolValidator],
        widget=Textarea(),
        help_text="This field is optional",
    )

    entry_into_force_date = DateInputFieldFixed(
        required=False,
        help_text="This field is optional",
    )

    policy_contact = CharField(
        required=False,
        max_length=255,
        validators=[SymbolValidator],
        help_text="This field is optional",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bind_nested_forms(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "ticket_name",
                "work_type",
                "assignment",
                "description",
                "entry_into_force_date",
                "policy_contact",
            ),
            Submit(
                "submit",
                "Create",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


TaskWorkflowDeleteForm = delete_form_for(TaskWorkflow)


class TaskWorkflowUpdateForm(TaskWorkflowAssigneeForm, ModelForm):
    title = CharField(
        label="Ticket name",
        max_length=255,
        validators=[SymbolValidator],
        error_messages={
            "required": "Enter a ticket name",
        },
    )
    description = CharField(
        validators=[SymbolValidator],
        widget=Textarea(),
        required=False,
    )
    eif_date = DateInputFieldFixed(
        label="Entry into force date",
        required=False,
    )
    policy_contact = CharField(
        required=False,
        max_length=40,
        validators=[SymbolValidator],
    )

    class Meta:
        model = TaskWorkflow
        fields = ["eif_date", "policy_contact"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["title"].initial = self.instance.summary_task.title
        self.fields["description"].initial = self.instance.summary_task.description

        self.fields["assignee"].help_text = ""
        try:
            self.fields["assignee"].initial = (
                self.instance.summary_task.assignees.assigned().get().user
            )
        except TaskAssignee.DoesNotExist:
            pass

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            "assignee",
            "eif_date",
            "policy_contact",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
                css_class="govuk-!-margin-right-2",
            ),
            HTML(
                f'<a class="govuk-link govuk-!-display-inline-block govuk-!-margin-top-2" href="{self.instance.get_url("detail")}">Back</a>',
            ),
        )

    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit)

        summary_task = instance.summary_task
        summary_task.title = self.cleaned_data["title"]
        summary_task.description = self.cleaned_data["description"]

        if commit:
            summary_task.save()

        return instance


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
        fields = ("title", "description", "automation_class_name")

    def __init__(self, *args, submit_title, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            "automation_class_name",
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


class TaskFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "search",
            "progress_state",
            "assignees",
            Field("work_type", css_class="govuk-!-width-full"),
            "assignment_status",
            Button(
                "submit",
                "Search and filter",
            ),
            HTML(
                f'<a class="govuk-button govuk-button--secondary" href="{self.clear_url}"> Clear </a>',
            ),
        )

    def init_fields(self):
        self.fields["assignees"].label_from_instance = (
            lambda obj: f"{obj.get_displayname()}"
        )


class TicketCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        error_messages={"required": "Enter your comment"},
        widget=forms.widgets.Textarea,
        max_length=5000,
    )

    class Meta:
        model = Comment
        fields = ("content",)

    def clean_content(self):
        content = self.cleaned_data["content"]
        html = markdown.markdown(text=content, extensions=["sane_lists", "tables"])
        content = bleach.clean(
            text=html,
            tags=markdown_tags_allowlist,
            attributes=[],
            strip=True,
        )
        return content


class TicketCommentCreateForm(TicketCommentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.textarea("content", rows=1, placeholder="Add a comment"),
            Button.secondary(
                "submit",
                "Add",
                data_prevent_double_click="true",
            ),
        )

    def save(self, user, task, commit=True):
        instance = super().save(commit=False)
        instance.author = user
        instance.task = task
        if commit:
            instance.save()
        return instance


class TicketCommentUpdateForm(TicketCommentForm):
    def __init__(self, *args, **kwargs):
        ticket_pk = kwargs.pop("ticket_pk")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.textarea("content", placeholder="Edit comment"),
            Div(
                Submit(
                    "submit",
                    "Save",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                HTML(
                    f"<a class='govuk-button govuk-button--secondary' href={reverse('workflow:task-workflow-ui-detail', kwargs={'pk':ticket_pk})}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )


class TicketCommentDeleteForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ()

    def __init__(self, *args, **kwargs):
        ticket_pk = kwargs.pop("ticket_pk")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Div(
                Submit(
                    "submit",
                    "Delete",
                    css_class="govuk-button--warning",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                HTML(
                    f"<a class='govuk-button govuk-button--secondary' href={reverse('workflow:task-workflow-ui-detail', kwargs={'pk':ticket_pk})}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )
