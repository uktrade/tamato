from datetime import datetime

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django.contrib.auth import get_user_model
from django.db import transaction
from django.forms import CharField
from django.forms import CheckboxSelectMultiple
from django.forms import Form
from django.forms import ModelChoiceField
from django.forms import ModelForm
from django.forms import ModelMultipleChoiceField
from django.forms import Textarea
from django.utils.timezone import make_aware

from common.fields import AutoCompleteField
from common.forms import BindNestedFormMixin
from common.forms import DateInputFieldFixed
from common.forms import delete_form_for
from common.validators import SymbolValidator
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate
from tasks.signals import set_current_instigator
from workbaskets.models import WorkBasket

User = get_user_model()


class TaskBaseForm(ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "progress_state",
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
            "progress_state": {
                "required": "Select a status",
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
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["progress_state"].label = "Status"

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


class AssignUsersForm(Form):
    users = ModelMultipleChoiceField(
        help_text="Select users to assign",
        widget=CheckboxSelectMultiple,
        queryset=User.objects.active_tms(),
        error_messages={"required": "Select one or more users to assign"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["users"].label_from_instance = lambda obj: obj.get_full_name()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "users",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    @transaction.atomic
    def assign_users(self, task: Task, user_instigator) -> list[TaskAssignee]:
        """Create TaskAssignee instances for the selected Users and return the
        TaskAssignees as a list."""
        set_current_instigator(user_instigator)

        assignees = [
            TaskAssignee(
                user=user,
                assignment_type=TaskAssignee.AssignmentType.GENERAL,
                task=task,
            )
            for user in self.cleaned_data["users"]
            if not TaskAssignee.objects.filter(
                user=user,
                assignment_type=TaskAssignee.AssignmentType.GENERAL,
                task=task,
            )
            .assigned()
            .exists()
        ]
        return TaskAssignee.objects.bulk_create(assignees)


class UnassignUsersForm(Form):
    assignees = ModelMultipleChoiceField(
        label="Users",
        help_text="Select users to unassign",
        widget=CheckboxSelectMultiple,
        queryset=TaskAssignee.objects.all(),
        error_messages={"required": "Select one or more users to unassign"},
    )

    def __init__(self, *args, **kwargs):
        self.task = kwargs.pop("task", None)
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["assignees"].queryset = self.task.assignees.order_by(
            "user__first_name",
            "user__last_name",
        ).exclude(unassigned_at__isnull=False)

        self.fields["assignees"].label_from_instance = (
            lambda obj: f"{obj.user.get_full_name()}"
        )

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "assignees",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    @transaction.atomic
    def unassign_users(self, user_instigator) -> int:
        """Set assignees as unassigned from their associated task and return the
        number of assignees that have been updated in this way."""
        set_current_instigator(user_instigator)

        assignees = self.cleaned_data["assignees"]
        for assignee in assignees:
            assignee.unassigned_at = make_aware(datetime.now())

        return TaskAssignee.objects.bulk_update(
            assignees,
            fields=["unassigned_at"],
        )


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
        help_text="Choose the most appropriate category, this will generate a pre-defined set of steps to complete the work",
        queryset=TaskWorkflowTemplate.objects.all(),
        error_messages={
            "required": "Choose a work type",
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


class TaskWorkflowUpdateForm(ModelForm):
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

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            "description",
            "eif_date",
            "policy_contact",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
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
