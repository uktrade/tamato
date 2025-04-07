from datetime import datetime

import bleach
import markdown
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils.timezone import make_aware

from common.validators import AlphanumericValidator
from common.validators import SymbolValidator
from common.validators import markdown_tags_allowlist
from tasks.models import Comment
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.signals import set_current_instigator
from workbaskets import models
from workbaskets import validators
from workbaskets.models import CreateWorkBasketAutomation
from workbaskets.util import serialize_uploaded_data

User = get_user_model()


class WorkbasketCreateForm(forms.ModelForm):
    """The form for creating a new workbasket."""

    title = forms.CharField(
        label="TOPS/Jira number",
        help_text=(
            "Your TOPS/Jira number is needed to associate your workbasket with your Jira ticket. "
            "You can find this number at the end of the web address for your Jira ticket. "
            "Your workbasket will be given a unique number that will be different to your TOPS/Jira number. "
        ),
        widget=forms.TextInput,
        validators=[validators.tops_jira_number_validator],
        required=True,
        error_messages={"unique": "A workbasket with this title already exists"},
    )

    reason = forms.CharField(
        label="Workbasket description",
        help_text="Summarise the changes that will be in this workbasket.",
        widget=forms.Textarea,
        validators=[
            AlphanumericValidator,
            SymbolValidator,
        ],
        required=True,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            Field.textarea("reason", rows=5),
            Submit(
                "submit",
                "Create",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = models.WorkBasket
        fields = ("title", "reason")


class WorkbasketUpdateForm(WorkbasketCreateForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "title",
            Field.textarea("reason", rows=5),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class WorkbasketDeleteForm(forms.Form):
    """Form used as part of deleting a workbasket."""

    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        workbasket = self.instance
        models_count = workbasket.tracked_models.count()
        if models_count:
            raise forms.ValidationError(
                f"Workbasket {workbasket.pk} contains {models_count} item(s), "
                f"but must be empty in order to permit deletion.",
            )

        return cleaned_data


class SelectableObjectField(forms.BooleanField):
    """Associates an object instance with a BooleanField."""

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop("obj")
        super().__init__(*args, **kwargs)


class SelectableObjectsForm(forms.Form):
    """
    Form used to dynamically build a variable number of selectable objects.

    The form's initially selected objects are given in the form's initial data.
    """

    FIELD_NAME_PREFIX = "selectableobject_"

    def __init__(self, *args, **kwargs):
        objects = kwargs.pop("objects", [])

        super().__init__(*args, **kwargs)

        for obj in objects:
            self.fields[SelectableObjectsForm.field_name_for_object(obj)] = (
                SelectableObjectField(
                    required=False,
                    obj=obj,
                    initial=str(obj.id) in [str(k) for k in self.initial.keys()],
                )
            )

    @classmethod
    def field_name_for_object(cls, obj):
        """Given an object, get its name representation for use in form field
        name attributes."""
        return f"{cls.FIELD_NAME_PREFIX}{obj.pk}"

    @classmethod
    def object_id_from_field_name(cls, name_value):
        """Given a field name from this form, extract the id of the associated
        object."""
        return name_value.replace(cls.FIELD_NAME_PREFIX, "")

    @property
    def cleaned_data_no_prefix(self):
        """Get cleaned_data without the form field's name prefix."""
        return {
            SelectableObjectsForm.object_id_from_field_name(key): value
            for key, value in self.cleaned_data.items()
        }


class WorkbasketCompareForm(forms.Form):
    data = forms.CharField(
        label="Compare worksheet data against the measures in this workbasket",
        widget=forms.Textarea(
            attrs={"placeholder": "Add your worksheet data here"},
        ),
        validators=[SymbolValidator],
    )

    def clean(self):
        if self.cleaned_data:
            serialized = serialize_uploaded_data(self.cleaned_data["data"])
            return {"data": serialized, "raw_data": self.cleaned_data["data"]}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.textarea("data", rows=10),
            Submit(
                "submit",
                "Compare",
                data_module="govuk-button--secondary",
                data_prevent_double_click="true",
            ),
        )


class WorkBasketAssignUsersForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        help_text="Select users to assign",
        widget=forms.CheckboxSelectMultiple,
        queryset=User.objects.all(),
        error_messages={"required": "Select one or more users to assign"},
    )
    assignment_type = forms.ChoiceField(
        choices=TaskAssignee.AssignmentType.choices,
        widget=forms.RadioSelect,
        error_messages={"required": "Select an assignment type"},
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.workbasket = kwargs.pop("workbasket", None)
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["users"].queryset = (
            User.objects.filter(
                Q(groups__name__in=["Tariff Managers", "Tariff Lead Profile"])
                | Q(is_superuser=True),
            )
            .filter(is_active=True)
            .distinct()
            .order_by("first_name", "last_name")
        )

        self.fields["users"].label_from_instance = lambda obj: obj.get_full_name()

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "users",
            Field.radios("assignment_type", inline=True),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    @transaction.atomic
    def assign_users(self, task):
        set_current_instigator(self.request.user)

        assignment_type = self.cleaned_data["assignment_type"]

        assignees = [
            TaskAssignee(
                user=user,
                assignment_type=assignment_type,
                task=task,
            )
            for user in self.cleaned_data["users"]
            if not TaskAssignee.objects.filter(
                user=user,
                assignment_type=assignment_type,
                task__workbasket=self.workbasket,
            )
            .assigned()
            .exists()
        ]
        return TaskAssignee.objects.bulk_create(assignees)


class WorkBasketUnassignUsersForm(forms.Form):
    assignees = forms.ModelMultipleChoiceField(
        label="Users",
        help_text="Select users to unassign",
        widget=forms.CheckboxSelectMultiple,
        queryset=TaskAssignee.objects.all(),
        error_messages={"required": "Select one or more users to unassign"},
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.workbasket = kwargs.pop("workbasket", None)
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["assignees"].queryset = self.workbasket.user_assignments.order_by(
            "user__first_name",
            "user__last_name",
        )

        self.fields["assignees"].label_from_instance = (
            lambda obj: f"{obj.user.get_full_name()} ({obj.get_assignment_type_display().lower()})"
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
    def unassign_users(self):
        set_current_instigator(self.request.user)

        assignees = self.cleaned_data["assignees"]
        for assignee in assignees:
            assignee.unassigned_at = make_aware(datetime.now())

        return TaskAssignee.objects.bulk_update(
            assignees,
            fields=["unassigned_at"],
        )


class WorkBasketCommentForm(forms.ModelForm):
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


class WorkBasketCommentCreateForm(WorkBasketCommentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.textarea("content", rows=1, placeholder="Add a comment"),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def save(self, user, workbasket, commit=True):
        instance = super().save(commit=False)
        instance.author = user
        instance.task = Task.objects.get(workbasket=workbasket)
        if commit:
            instance.save()
        return instance


class WorkBasketCommentUpdateForm(WorkBasketCommentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.textarea("content", placeholder="Add a comment"),
            Div(
                Submit(
                    "submit",
                    "Save",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                HTML(
                    f"<a class='govuk-button govuk-button--secondary' href={reverse('workbaskets:current-workbasket')}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )


class WorkBasketCommentDeleteForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ()

    def __init__(self, *args, **kwargs):
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
                    f"<a class='govuk-button govuk-button--secondary' href={reverse('workbaskets:current-workbasket')}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )


class AutomationCreateWorkBasketForm(forms.Form):
    """Form for creating workbaskets via CreateWorkBasketAutomation."""

    def __init__(self, *args, **kwargs):
        self.automation: CreateWorkBasketAutomation = kwargs.pop("automation")

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Submit(
                "submit",
                "Run",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        self.automation.can_run_automation()
        return self.cleaned_data
