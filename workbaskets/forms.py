from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.validators import AlphanumericValidator
from common.validators import SymbolValidator
from workbaskets import models
from workbaskets import validators


class WorkbasketCreateForm(forms.ModelForm):
    """The form for creating a new workbasket."""

    title = forms.CharField(
        label="Tops/Jira number",
        help_text=(
            "Your Tops/Jira number is needed to associate your workbasket with your Jira ticket. "
            "You can find this number at the end of the web address for your Jira ticket. "
            "Your workbasket will be given a unique number that may be different to your Tops/Jira number. "
        ),
        widget=forms.TextInput,
        validators=[validators.tops_jira_number_validator],
        required=True,
    )

    reason = forms.CharField(
        label="Description",
        help_text="Add your notes here.",
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
        self.helper.layout[2].value = "Save"


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
        objects = kwargs.pop("objects")

        super().__init__(*args, **kwargs)

        for obj in objects:
            self.fields[
                SelectableObjectsForm.field_name_for_object(obj)
            ] = SelectableObjectField(
                required=False,
                obj=obj,
                initial=str(obj.id) in [str(k) for k in self.initial.keys()],
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
