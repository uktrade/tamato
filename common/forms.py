import re
from collections import defaultdict
from datetime import date
from typing import Dict
from typing import List
from typing import Type

from crispy_forms_gds.fields import DateInputField
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.contrib.postgres.forms.ranges import DateRangeField
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.forms.renderers import get_default_renderer
from django.forms.utils import ErrorList

from common.util import TaricDateRange
from common.util import get_model_indefinite_article
from common.validators import AlphanumericValidator
from common.widgets import FormSetFieldWidget
from common.widgets import MultipleFileInput
from common.widgets import RadioNestedWidget

MESSAGE_FORM_MIXIN = "This field requires the form to use BindNestedFormMixin"
MESSAGE_BIND_FORMS = "Nested forms must be instantiated with bind_nested_forms in the subclass's __init__"


class BindNestedFormMixin:
    """
    Form classes that use the RadioNested form field must inherit from this.

    in order to instantiate and validate nested forms.
    """

    def get_bound_form(self, form_class, *args, **kwargs):
        if issubclass(form_class, FormSet):
            formset_kwargs = kwargs.copy()
            if "initial" in formset_kwargs:
                formset_kwargs.pop("initial")
            formset_initial = None
            if kwargs.get("initial"):
                formset_initial = kwargs.get("initial").get(
                    form_class.prefix,
                )

            bound_form = form_class(
                *args,
                **formset_kwargs,
                initial=formset_initial,
            )
        else:
            bound_form = form_class(*args, **kwargs)
        return bound_form

    def bind_nested_forms(self, *args, **kwargs):
        # this mixin does not support ModelForm as subforms
        kwargs.pop("instance", None)

        for name, field in self.fields.items():
            if isinstance(field, RadioNested):
                all_forms = {}
                for choice, form_list in field.nested_forms.items():
                    nested_forms = []

                    for form_class in form_list:
                        nested_forms.append(
                            self.get_bound_form(form_class, *args, **kwargs),
                        )
                    all_forms[choice] = nested_forms
                field.bind_nested_forms(all_forms)

            elif isinstance(field, FormSetField):
                bound_forms = []
                for form_class in field.nested_forms:
                    bound_form = self.get_bound_form(form_class, *args, **kwargs)
                    bound_forms.append(bound_form)
                field.bind_nested_forms(bound_forms)

    def formset_submit(self):
        nested_formset_submit = [
            field.nested_formset_submit
            for field in self.fields.values()
            if isinstance(field, RadioNested) or isinstance(field, FormSetField)
        ]
        return any(nested_formset_submit)

    def is_valid(self):
        return super().is_valid() and not self.formset_submit()

    @staticmethod
    def clean_form(form, cleaned_data):
        if form.is_valid():
            data = form.cleaned_data
            if isinstance(form, FormSet):
                # cleaned_data from a formset is a list
                data = {form.prefix: form.cleaned_data}
            cleaned_data.update(data)

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data.copy()

        for field_name in self.cleaned_data.keys():
            field = self.fields[field_name]
            if isinstance(field, RadioNested):
                all_forms = [
                    form
                    for form_list in field.nested_forms.values()
                    for form in form_list
                ]
                for form in all_forms:
                    self.clean_form(form, cleaned_data)

            elif isinstance(field, FormSetField):
                for form in field.nested_forms:
                    self.clean_form(form, cleaned_data)

        return cleaned_data


class RadioNested(forms.TypedChoiceField):
    """
    Radio buttons with a dictionary of nested forms that are displayed when the
    option is selected. Multiple or zero forms or formsets can be nested under
    each option.

    Example usage:

    can_contact = RadioNested(
        label="Can we contact you?",
        choices=[("YES", "Yes"), ("NO", "No")],
        nested_forms={
            "YES": [ContactTimePreferenceForm, ContactMethodDetailsFormSet],
            "NO": [],
        },
    )

    In the form class bind_nested_forms must be called after super().__init__:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # kwargs for the nested forms can be modified here
        self.bind_nested_forms(*args, **kwargs)
    """

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
                ), MESSAGE_BIND_FORMS
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
        assert isinstance(form, BindNestedFormMixin), MESSAGE_FORM_MIXIN
        return super().get_bound_field(form, field_name)


class FormSetField(forms.Field):
    widget = FormSetFieldWidget
    template_name = "django/forms/field.html"

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
        nested_formset_submit = []
        for form in self.nested_forms:
            assert isinstance(form, forms.Form) or isinstance(
                form,
                FormSet,
            ), MESSAGE_BIND_FORMS
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
        assert isinstance(form, BindNestedFormMixin), MESSAGE_FORM_MIXIN
        return super().get_bound_field(form, field_name)


class DescriptionHelpBox(Div):
    template = "components/description_help.jinja"


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


class DateInputFieldTakesParameters(DateInputField):
    def __init__(self, day, month, year, **kwargs):
        error_messages = {
            "required": "Enter the day, month and year",
            "incomplete": "Enter the day, month and year",
        }
        fields = (day, month, year)

        forms.MultiValueField.__init__(
            self,
            error_messages=error_messages,
            fields=fields,
            **kwargs,
        )

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
        help_text="You may enter HTML formatting if required. See the guide below "
        "for more information.",
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field("validity_start", context={"legend_size": "govuk-label--s"}),
            Field.textarea("description", label_size=Size.SMALL, rows=5),
            DescriptionHelpBox(),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        fields = ("description", "validity_start")


class ValidityPeriodBaseForm(forms.Form):
    start_date = DateInputFieldFixed(label="Start date")
    end_date = DateInputFieldFixed(
        label="End date",
        required=False,
    )
    valid_between = GovukDateRangeField(required=False)

    def clean_validity_period(
        self,
        cleaned_data,
        valid_between_field_name="valid_between",
        start_date_field_name="start_date",
        end_date_field_name="end_date",
    ):
        start_date = cleaned_data.pop(start_date_field_name, None)
        end_date = cleaned_data.pop(end_date_field_name, None)

        # Data may not be present, e.g. if the user skips ahead in the sidebar
        valid_between = self.initial.get(valid_between_field_name)
        if end_date and start_date and end_date < start_date:
            if valid_between:
                if start_date != valid_between.lower:
                    self.add_error(
                        start_date_field_name,
                        "The start date must be the same as or before the end date.",
                    )
                if end_date != self.initial[valid_between_field_name].upper:
                    self.add_error(
                        end_date_field_name,
                        "The end date must be the same as or after the start date.",
                    )
            else:
                self.add_error(
                    end_date_field_name,
                    "The end date must be the same as or after the start date.",
                )
        cleaned_data[valid_between_field_name] = TaricDateRange(start_date, end_date)

        if start_date:
            day, month, year = (start_date.day, start_date.month, start_date.year)
            self.fields[start_date_field_name].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

        if end_date:
            day, month, year = (end_date.day, end_date.month, end_date.year)
            self.fields[end_date_field_name].initial = date(
                day=int(day),
                month=int(month),
                year=int(year),
            )

    def clean(self):
        cleaned_data = super().clean()
        self.clean_validity_period(cleaned_data)
        return cleaned_data


class ValidityPeriodForm(ValidityPeriodBaseForm, forms.ModelForm):
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


class CreateDescriptionForm(DescriptionForm):
    description = forms.CharField(
        widget=forms.Textarea,
        help_text=(
            "You can use HTML formatting if required. See the help text "
            "below for more information."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["validity_start"].label = "Start date"


class DeleteForm(forms.ModelForm):
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
                    f"<a class='govuk-button govuk-button--secondary' href={self.instance.get_url()}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
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

    If the form POST data contains an "ADD" field with the value "1", the
    formset will be redisplayed with a new empty form appended.

    Deleting a subform will also redisplay the formset, with the order of the
    forms preserved.
    """

    extra = 0
    can_order = False
    can_delete = True
    can_delete_extra = True
    max_num = 1000
    min_num = 0
    absolute_max = 1000
    validate_min = False
    validate_max = False
    prefix = None
    renderer = get_default_renderer()

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,  # not used but expected by the base class
        initial=None,
        error_class=ErrorList,
        form_kwargs=None,
        error_messages=None,
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

        messages = {}
        for cls in reversed(type(self).__mro__):
            messages.update(getattr(cls, "default_error_messages", {}))
        if error_messages is not None:
            messages.update(error_messages)
        self.error_messages = messages

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
                if value or self.formset_action == "ADD":
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

        self.initial = initial

        if initial:
            num_initial = (
                len(initial)
                if len(initial) == len(formset_initial.values())
                else len(formset_initial.values())
            )
        else:
            num_initial = len(formset_initial.values())

        if num_initial < 1:
            data[f"{self.prefix}-ADD"] = "1"

        # update management data
        data[f"{self.prefix}-INITIAL_FORMS"] = num_initial
        data[f"{self.prefix}-TOTAL_FORMS"] = num_initial
        self.data = data

    @property
    def formset_add_delete(self):
        """Re-present the form to show the result of adding another form or
        deleting an existing one."""
        if self.formset_action == "ADD" or self.formset_action == "DELETE":
            return True
        return False

    def is_valid(self):
        """Invalidates the formset if "Add another" or "Delete" are submitted,
        to redisplay the formset with an extra empty form or the selected form
        removed."""

        if self.formset_add_delete:
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
        min_num = forms.formsets.DEFAULT_MIN_NUM
    if max_num is None:
        max_num = forms.formsets.DEFAULT_MAX_NUM
    # absolute_max is a hard limit on forms instantiated, to prevent
    # memory-exhaustion attacks. Default to max_num + DEFAULT_MAX_NUM
    # (which is 2 * DEFAULT_MAX_NUM if max_num is None in the first place).
    if absolute_max is None:
        absolute_max = max_num + forms.formsets.DEFAULT_MAX_NUM
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


def unprefix_formset_data(prefix, data):
    """Takes form data and filters out everything but the formset data for a
    given formset prefix."""
    output = []
    formset_data = {}

    pattern = f"({prefix}-([0-9]-)?DELETE|ADD|INITIAL_FORMS|MAX_NUM_FORMS|MIN_NUM_FORMS|TOTAL_FORMS)+"
    keys_to_delete = []

    for key in data.keys():
        found = re.search(pattern, key)
        if found:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del data[key]

    for k, v in data.items():
        if prefix in k:
            formset_data[k] = v

    if not formset_data:
        return []

    num_items = len(formset_data.items())

    for i in range(0, num_items):
        subform_initial = {}
        for k, v in formset_data.items():
            if k.startswith(f"{prefix}-{i}-"):
                subform_initial[k.split(f"{prefix}-{i}-")[1]] = v
        if subform_initial:
            output.append(subform_initial)

    for k, v in formset_data.items():
        subform_initial = {}
        if k.startswith(f"{prefix}-__prefix__-"):
            subform_initial[k.split(f"{prefix}-__prefix__-")[1]] = v
    if subform_initial:
        output.append(subform_initial)

    return output


def formset_add_or_delete(data):
    """Find any {prefix}-ADD or {prefix}-DELETE in submitted data and return the
    result as a boolean."""
    formset_data = {}
    for k, v in data.items():
        if k.endswith("-ADD") or k.endswith("-DELETE"):
            formset_data[k] = v
    if len(formset_data) > 0:
        return True
    return False


class FormSetSubmitMixin:
    @property
    def formset_submitted(self):
        return formset_add_or_delete(self.data)

    @property
    def whole_form_submit(self):
        return bool(self.data.get("submit"))


class MultipleFileField(forms.FileField):
    """FileField that allows multiple files to be selected."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        cleaned_data = super().clean
        files = []
        if isinstance(data, (list, tuple)):
            files = [cleaned_data(file, initial) for file in data]
        else:
            files = cleaned_data(data, initial)
        return files


class HomeSearchForm(forms.Form):
    search_term = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Search by tariff element name or ID"},
        ),
        validators=[AlphanumericValidator],
        max_length=18,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Div(
                Field.text("search_term"),
                Submit(
                    "submit",
                    "Search",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                css_id="homepage-search-form",
            ),
        )


class SerializableFormMixin:
    """Provides a default implementation of `serializable_data()` that can be
    used to obtain form data that can be serialized, or more specifically,
    stored to a `JSONField` field."""

    ignored_data_key_regexs = [
        "^csrfmiddlewaretoken$",
        "^measure_create_wizard-current_step$",
        "^submit$",
        "-ADD$",
        "-DELETE$",
        "_autocomplete$",
        "INITIAL_FORMS$",
        "MAX_NUM_FORMS$",
        "MIN_NUM_FORMS$",
        "TOTAL_FORMS$",
    ]
    """
    Regexs of keys that may appear in a Form's `data` dictionary attribute and
    which should be ignored when creating a serializable version of `data`.

    Override this on a per form basis if there are other, redundant keys that
    should be ignored. See the default implementation of
    `SerializableFormMixin.get_serializable_data_keys()` to see how this class
    attribute is used.
    """

    def get_serializable_data_keys(self) -> List[str]:
        """
        Default implementation returning a list of the `Form.data` attribute's
        keys used when serializing `data`.

        Override this function if neither `ignored_data_key_regexs` or this
        default implementation is sufficient for identifying which of
        `Form.data`'s keys should be used during a call to this mixin's
        `serializable_data()` method.
        """
        combined_regexs = "(" + ")|(".join(self.ignored_data_key_regexs) + ")"
        return [k for k in self.data.keys() if not re.search(combined_regexs, k)]

    def serializable_data(self, remove_key_prefix: str = "") -> Dict:
        """
        Return serializable form data that can be serialized / stored as, say,
        `django.db.models.JSONField` which can be used to recreate a valid form.

        If `remove_key_prefix` is a non-empty string, then the keys in the
        returned dictionary will be stripped of that string where it appears as
        a key prefix in the origin `data` dictionary.

        Note that this method should only be used immediately after a successful
        call to the Form's is_valid() if the data that it returns is to be used
        to recreate a valid form.
        """
        serialized_data = {}
        data_keys = self.get_serializable_data_keys()

        for data_key in data_keys:
            serialized_key = data_key

            if (
                remove_key_prefix
                and len(remove_key_prefix) < len(data_key)
                and data_key.startswith(remove_key_prefix)
            ):
                prefix = f"{remove_key_prefix}-"
                serialized_key = data_key.replace(prefix, "")

            serialized_data[serialized_key] = self.data[data_key]

        return serialized_data

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        """
        Get a serializable dictionary of arguments that can be used to
        initialise the form. The `kwargs` parameter is the Python version of
        kwargs that are used to initialise the form and is normally provided by
        the same caller as would init the form (i.e. the view).

        For instance, a SelectableObjectsForm subclass
        requires a valid `objects` parameter to correctly construct and
        validate the form, so we'd expect `kwargs` dictionary containing
        an `objects` element.
        """
        return {}

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        """
        Get a dictionary of arguments for use in initialising the form.

        The 'form_kwargs` parameter is the serialized (actually, serializable)
        version of the form's kwargs that require deserializing to their Python
        representation.
        """
        return {}


class ExtraErrorFormMixin:
    def add_extra_error(self, field, error):
        """
        A modification of Django's add_error method that allows us to add data
        to self._errors under custom keys that are not field names or
        NON_FIELD_ERRORS.

        Used to pass errors to the React form.
        """
        if not isinstance(error, ValidationError):
            error = ValidationError(error)

        if hasattr(error, "error_dict"):
            if field is not None:
                raise TypeError(
                    "The argument `field` must be `None` when the `error` "
                    "argument contains errors for multiple fields.",
                )
            else:
                error = error.error_dict
        else:
            error = {field or NON_FIELD_ERRORS: error.error_list}

        for field, error_list in error.items():
            if field not in self.errors:
                self._errors[field] = self.error_class()
            self._errors[field].extend(error_list)
            if field in self.cleaned_data:
                del self.cleaned_data[field]


class DummyForm(forms.Form):
    """Form with no fields used as a placeholder for when the view requires a
    form class."""
