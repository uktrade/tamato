from collections import defaultdict
from datetime import date
from typing import Type

from crispy_forms_gds.fields import DateInputField
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.contrib.postgres.forms.ranges import DateRangeField
from django.core.exceptions import ValidationError
from django.forms import TypedChoiceField
from django.forms import formsets
from django.forms.renderers import get_default_renderer
from django.forms.utils import ErrorList
from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe

from common.util import TaricDateRange
from common.util import get_model_indefinite_article
from common.widgets import RadioNestedWidget


class BindNestedFormMixin:
    def bind_nested_forms(self, *args, **kwargs):
        if kwargs.get("instance"):
            kwargs.pop("instance")  # this mixin does not support ModelForm as subforms

        for name, field in self.fields.items():

            if isinstance(field, RadioNested):
                all_forms = {}
                for choice, form_list in field.nested_forms.items():
                    nested_forms = []

                    for form_class in form_list:
                        bound_form = form_class(*args, **kwargs)
                        nested_forms.append(bound_form)
                    all_forms[choice] = nested_forms
                field.bind_nested_forms(all_forms)

    def formset_submit(self):
        nested_formset_submit = [
            field.nested_formset_submit
            for field in self.fields.values()
            if isinstance(field, RadioNested)
        ]
        return any(nested_formset_submit)

    def is_valid(self):
        return super().is_valid() and not self.formset_submit()

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data.copy()

        for field_name in self.cleaned_data.keys():  # /PS-IGNORE
            field = self.fields[field_name]
            if isinstance(field, RadioNested):  # /PS-IGNORE
                all_forms = [
                    form
                    for form_list in field.nested_forms.values()
                    for form in form_list
                ]
                for form in all_forms:
                    if form.is_valid():
                        data = form.cleaned_data
                        if isinstance(form, FormSet):
                            # cleaned_data from a formset is a list
                            data = {form.prefix: form.cleaned_data}
                        cleaned_data.update(data)
        return cleaned_data


class RadioNested(TypedChoiceField):
    MESSAGE_FORM_MIXIN = "This field requires the form to use BindNestedFormMixin"
    MESSAGE_BIND_FORMS = "Nested forms must be instantiated with bind_nested_forms in the subclass's __init__"
    widget = RadioNestedWidget

    def __init__(self, nested_forms=None, *args, **kwargs):
        self.nested_forms = nested_forms
        self.nested_formset_submit = False
        super().__init__(*args, **kwargs)
        self.widget.nested_forms = nested_forms

    def bind_nested_forms(self, forms):
        self.nested_forms = forms
        self.widget.bind_nested_forms(forms)

    def validate(self, value):
        super().validate(value)
        # only need to validate the nested form of the selected option
        nested_formset_submit = []
        if value:
            for form in self.nested_forms[value]:
                assert isinstance(form, forms.Form) or isinstance(
                    form,
                    FormSet,
                ), self.MESSAGE_BIND_FORMS
                if not form.is_valid():
                    if isinstance(form, FormSet):
                        if form.formset_action is not None:
                            nested_formset_submit.append(True)
                        for errors in form.errors:
                            for e in errors.values():
                                if e:
                                    raise ValidationError(e)
                        for e in form.non_form_errors():
                            if e:
                                raise ValidationError(e)
                    else:
                        for e in form.errors.values():
                            raise ValidationError(e)

        self.nested_formset_submit = any(nested_formset_submit)

    def get_bound_field(self, form, field_name):
        assert isinstance(form, BindNestedFormMixin), self.MESSAGE_FORM_MIXIN
        return super().get_bound_field(form, field_name)


class DescriptionHelpBox(Div):
    template = "components/description_help.jinja"


class AutocompleteWidget(Widget):
    template_name = "components/autocomplete.jinja"

    def get_context(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        display_string = ""
        if value:
            display_string = value.structure_code
            if value.structure_description:
                display_string = f"{display_string} - {value.structure_description}"

        return {
            "widget": {
                "name": name,
                "value": value.pk if value else None,
                "display_value": display_string,
                **self.attrs,
            },
        }

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)


class DateInputFieldFixed(DateInputField):
    def compress(self, data_list):
        day, month, year = data_list or [None, None, None]
        if day and month and year:
            try:
                return date(day=int(day), month=int(month), year=int(year))
            except ValueError as e:
                raise ValidationError(str(e).capitalize()) from e
        else:
            return None


class GovukDateRangeField(DateRangeField):
    base_field = DateInputFieldFixed

    def clean(self, value):
        """Validate the date range input `value` should be a 2-tuple or list or
        datetime objects or None."""
        clean_data = []
        errors = []
        if self.disabled and not isinstance(value, list):
            value = self.widget.decompress(value)

        # start date is always required
        if not value:
            raise ValidationError(self.error_messages["required"], code="required")

        # somehow we didn't get a list or tuple of datetimes
        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        for i, (field, value) in enumerate(zip(self.fields, value)):
            limit = ("start", "end")[i]

            if value in self.empty_values and (
                limit == "lower" or self.require_all_fields
            ):
                error = ValidationError(
                    self.error_messages[f"{limit}_required"],
                    code=f"{limit}_required",
                )
                error.subfield = i
                raise error

            try:
                clean_data.append(field.clean(value))
            except ValidationError as e:
                for error in e.error_list:
                    if "Enter a valid date" in str(error):
                        error.message = f"Enter a valid {limit} date."
                    error.subfield = i
                    errors.append(error)

        if errors:
            raise ValidationError(errors)

        out = self.compress(clean_data)
        self.validate(out)
        self.run_validators(out)
        return out


class DescriptionForm(forms.ModelForm):
    validity_start = DateInputFieldFixed(
        label="Start date",
    )

    description = forms.CharField(
        help_text="Edit or overwrite the existing description",
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field("validity_start", context={"legend_size": "govuk-label--s"}),
            Field.textarea("description", label_size=Size.SMALL, rows=5),
            Submit("submit", "Save"),
        )

    class Meta:
        fields = ("description", "validity_start")


class ValidityPeriodForm(forms.ModelForm):
    start_date = DateInputFieldFixed(label="Start date")
    end_date = DateInputFieldFixed(
        label="End date",
        required=False,
    )
    valid_between = GovukDateRangeField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["end_date"].help_text = (
            f"Leave empty if {get_model_indefinite_article(self.instance)} "
            f"{self.instance._meta.verbose_name} is needed for an unlimited time"
        )

        if self.instance.valid_between:
            if self.instance.valid_between.lower:
                self.fields["start_date"].initial = self.instance.valid_between.lower
            if self.instance.valid_between.upper:
                self.fields["end_date"].initial = self.instance.valid_between.upper

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.pop("start_date", None)
        end_date = cleaned_data.pop("end_date", None)

        # Data may not be present, e.g. if the user skips ahead in the sidebar
        valid_between = self.initial.get("valid_between")
        if valid_between and end_date and start_date and end_date < start_date:
            if start_date != valid_between.lower:
                self.add_error(
                    "start_date",
                    "The start date must be the same as or before the end date.",
                )
            if end_date != self.initial["valid_between"].upper:
                self.add_error(
                    "end_date",
                    "The end date must be the same as or after the start date.",
                )
        cleaned_data["valid_between"] = TaricDateRange(start_date, end_date)

        if start_date:
            day, month, year = (start_date.day, start_date.month, start_date.year)
            self.fields["start_date"].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

        if end_date:
            day, month, year = (end_date.day, end_date.month, end_date.year)
            self.fields["end_date"].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

        return cleaned_data


class CreateDescriptionForm(DescriptionForm):
    description = forms.CharField(
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["validity_start"].label = "Description start date"


class DeleteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Submit("submit", "Delete", css_class="govuk-button--warning"),
        )


def delete_form_for(for_model: Type) -> Type[DeleteForm]:
    """Returns a Form class that exposes a button for confirming the deletion of
    a model of the passed type."""

    class ModelDeleteForm(DeleteForm):
        class Meta:
            model = for_model
            fields = ()

    return ModelDeleteForm


class FormSet(forms.BaseFormSet):
    """
    Adds the ability to add another form to the formset on submit.

    If the form POST data contains an "ADD" field with the value "1", the formset
    will be redisplayed with a new empty form appended.

    Deleting a subform will also redisplay the formset, with the order of the forms
    preserved.
    """

    extra = 0
    can_order = False
    can_delete = True
    max_num = 1000
    min_num = 0
    absolute_max = 1000
    validate_min = False
    validate_max = False
    prefix = None

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,  # not used but expected by the base class
        initial=None,
        error_class=ErrorList,
        form_kwargs=None,
    ):
        # Not calling super().__init__() here because it overwrites any custom prefix we try to
        # pass to the formset and its subforms with the default value from the above 'prefix' kwarg
        self.prefix = self.prefix or self.get_default_prefix()
        self.is_bound = data is not None or files is not None
        self.auto_id = auto_id
        self.data = data or {}
        self.files = files or {}
        self.initial = initial
        self.form_kwargs = form_kwargs or {}
        self.error_class = error_class
        self._errors = None
        self._non_form_errors = None

        # If we have form data, then capture the any user "add form" or
        # "delete form" actions.
        self.formset_action = None
        self.is_formset = True  # required by templates
        if f"{self.prefix}-ADD" in self.data:
            self.formset_action = "ADD"
        else:
            for field in self.data:
                if self.prefix in field and field.endswith("-DELETE"):
                    self.formset_action = "DELETE"
                    break

        data = self.data.copy()

        formset_initial = defaultdict(dict)
        delete_forms = []
        for field, value in self.data.items():

            # filter out non-field data
            if field.startswith(f"{self.prefix}-"):
                form, field_name = field.rsplit("-", 1)

                # remove from data, so we can rebuild later
                if form != self.prefix:
                    del data[field]

                # group by subform
                if value:
                    formset_initial[form].update({field_name: value})

                if field_name == "DELETE" and value == "1":
                    delete_forms.append(form)

        # ignore management form
        try:
            del formset_initial[self.prefix]
        except KeyError:
            pass

        # ignore deleted forms
        for form in delete_forms:
            del formset_initial[form]

            # leave DELETE field in data for is_valid
            data[f"{form}-DELETE"] = 1

        for i, (form, form_initial) in enumerate(formset_initial.items()):
            for field, value in form_initial.items():

                # convert submitted value to python object
                form_field = self.form.declared_fields.get(field)
                if form_field:
                    form_initial[field] = form_field.widget.value_from_datadict(
                        form_initial,
                        {},
                        field,
                    )

                # reinsert into data, with updated numbering
                data[f"{self.prefix}-{i}-{field}"] = value

        self.initial = list(formset_initial.values())
        num_initial = len(self.initial)

        if num_initial < 1:
            data[f"{self.prefix}-ADD"] = "1"

        # update management data
        data[f"{self.prefix}-INITIAL_FORMS"] = num_initial
        data[f"{self.prefix}-TOTAL_FORMS"] = num_initial
        self.data = data

    def is_valid(self):
        """Invalidates the formset if "Add another" or "Delete" are submitted,
        to redisplay the formset with an extra empty form or the selected form
        removed."""
        # Re-present the form to show the result of adding another form or
        # deleting an existing one.
        if self.formset_action == "ADD" or self.formset_action == "DELETE":
            return False

        # An empty set of forms is valid.
        if self.total_form_count() == 0 and self.min_num == 0:
            return True

        return super().is_valid()


def formset_factory(
    form,
    prefix=None,
    formset=forms.BaseFormSet,
    extra=1,
    can_order=False,
    can_delete=False,
    max_num=None,
    validate_max=False,
    min_num=None,
    validate_min=False,
    absolute_max=None,
    can_delete_extra=True,
    renderer=None,
):
    """
    Return a FormSet for the given form class.  # /PS-IGNORE.

    This function is basically the same as the one in django but adds 'prefix'
    to the formset's attrs.
    """
    if min_num is None:
        min_num = formsets.DEFAULT_MIN_NUM
    if max_num is None:
        max_num = formsets.DEFAULT_MAX_NUM
    # absolute_max is a hard limit on forms instantiated, to prevent
    # memory-exhaustion attacks. Default to max_num + DEFAULT_MAX_NUM
    # (which is 2 * DEFAULT_MAX_NUM if max_num is None in the first place).
    if absolute_max is None:
        absolute_max = max_num + formsets.DEFAULT_MAX_NUM
    if max_num > absolute_max:
        raise ValueError("'absolute_max' must be greater or equal to 'max_num'.")
    attrs = {
        "form": form,
        "prefix": prefix,
        "extra": extra,
        "can_order": can_order,  # /PS-IGNORE
        "can_delete": can_delete,
        "can_delete_extra": can_delete_extra,
        "min_num": min_num,
        "max_num": max_num,
        "absolute_max": absolute_max,
        "validate_min": validate_min,
        "validate_max": validate_max,
        "renderer": renderer or get_default_renderer(),
    }
    return type(form.__name__ + "FormSet", (formset,), attrs)
