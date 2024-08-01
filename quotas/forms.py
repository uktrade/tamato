import datetime
from typing import Dict
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView

from common.serializers import deserialize_date, serialize_date
from common.fields import AutoCompleteField
from common.forms import BindNestedFormMixin
from common.forms import FormSet
from common.forms import FormSetField
from common.forms import FormSetSubmitMixin
from common.forms import RadioNested
from common.forms import ValidityPeriodBaseForm
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.forms import formset_factory
from common.forms import unprefix_formset_data
from common.util import validity_range_contains_range
from common.validators import SymbolValidator
from common.validators import UpdateType
from common.views import WithPaginationListMixin
from geo_areas.models import GeographicalArea
from measures.models import MeasurementUnit
from quotas import models
from quotas import validators
from quotas.constants import QUOTA_EXCLUSIONS_FORMSET_PREFIX
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX
from quotas.constants import QUOTA_ORIGINS_FORMSET_PREFIX
from workbaskets.forms import SelectableObjectsForm

RELATIONSHIP_TYPE_HELP_TEXT = "Select the relationship type for the quota association"
COEFFICIENT_HELP_TEXT = "Select the coefficient for the quota association."
CATEGORY_HELP_TEXT = "Categories are required for the TAP database but will not appear as a TARIC3 object in your workbasket"
SAFEGUARD_HELP_TEXT = (
    "Once the quota category has been set as ‘Safeguard’, this cannot be changed"
)
START_DATE_HELP_TEXT = "If possible, avoid putting a start date in the past as this may cause issues with CDS downstream"
ORDER_NUMBER_HELP_TEXT = "The order number must begin with 05 and be 6 digits long. Licensed quotas must begin 054 and safeguards must begin 058"


class QuotaFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Field.text("order_number", label_size=Size.SMALL),
            Field.text("origin", label_size=Size.SMALL),
            Field.radios("mechanism", legend_size=Size.SMALL),
            Field.radios("category", legend_size=Size.SMALL),
            Field.radios("active_state", legend_size=Size.SMALL),
            Field.text("current_work_basket", label_size=Size.SMALL),
            Button("submit", "Search and Filter", css_class="govuk-!-margin-top-6"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
            ),
        )


QuotaDeleteForm = delete_form_for(models.QuotaOrderNumber)


class QuotaDefinitionFilterForm(forms.Form):
    quota_type = forms.MultipleChoiceField(
        label="View by",
        choices=[
            ("sub_quotas", "Sub-quotas"),
            ("blocking_periods", "Blocking periods"),
            ("suspension_periods", "Suspension periods"),
        ],
        widget=forms.RadioSelect(),
    )

    def __init__(self, *args, **kwargs):
        quota_type_initial = kwargs.pop("form_initial")
        object_sid = kwargs.pop("object_sid")
        super().__init__(*args, **kwargs)
        self.fields["quota_type"].initial = quota_type_initial
        self.helper = FormHelper()

        clear_url = reverse_lazy(
            "quota_definition-ui-list",
            kwargs={"sid": object_sid},
        )

        self.helper.layout = Layout(
            Field.radios("quota_type", label_size=Size.SMALL),
            Button("submit", "Apply"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary" href="{clear_url}">Restore defaults</a>',
            ),
        )


class QuotaOriginExclusionsForm(forms.Form):
    exclusion = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),  # modified in __init__
        help_text="Select a country to be excluded:",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["exclusion"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        self.fields["exclusion"].label_from_instance = (
            lambda obj: f"{obj.area_id} - {obj.description}"
        )


QuotaOriginExclusionsFormSet = formset_factory(
    QuotaOriginExclusionsForm,
    prefix=QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX,
    formset=FormSet,
    min_num=0,
    max_num=100,
    extra=0,
    validate_min=True,
    validate_max=True,
)


class QuotaUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "valid_between",
            "category",
        ]

    category = forms.ChoiceField(
        label="",
        choices=validators.QuotaCategory.choices,
        error_messages={"invalid_choice": "Please select a valid category"},
    )

    def clean_category(self):
        value = self.cleaned_data.get("category")
        # the widget is disabled and data is not submitted. fall back to instance value
        if not value:
            return self.instance.category
        if (
            self.instance.category == validators.QuotaCategory.SAFEGUARD
            and value != validators.QuotaCategory.SAFEGUARD
        ):
            raise ValidationError(SAFEGUARD_HELP_TEXT)
        return value

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        self.geo_area_options = kwargs.pop("geo_area_options")
        self.existing_origins = kwargs.pop("existing_origins")
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.set_initial_data(*args, **kwargs)
        self.init_layout(self.request)

    def set_initial_data(self, *args, **kwargs):
        self.fields["category"].initial = self.instance.category

    def init_fields(self):
        if self.instance.category == validators.QuotaCategory.SAFEGUARD:
            self.fields["category"].required = False
            self.fields["category"].widget = forms.Select(
                choices=[
                    (
                        validators.QuotaCategory.SAFEGUARD.value,
                        validators.QuotaCategory.SAFEGUARD.label,
                    ),
                ],
                attrs={"disabled": True},
            )
            self.fields["category"].help_text = SAFEGUARD_HELP_TEXT
        else:
            self.fields["category"].choices = validators.QuotaCategoryEditing.choices
            self.fields["category"].help_text = CATEGORY_HELP_TEXT

        self.fields["start_date"].help_text = START_DATE_HELP_TEXT

    def get_origins_initial(self):
        initial = [
            {
                "id": o.pk,  # unique identifier used by react
                "pk": o.pk,
                "exclusions": [
                    {"pk": e.pk, "id": e.excluded_geographical_area.pk}
                    for e in o.quotaordernumberoriginexclusion_set.current()
                ],
                "geographical_area": o.geographical_area.pk,
                "start_date_0": o.valid_between.lower.day,
                "start_date_1": o.valid_between.lower.month,
                "start_date_2": o.valid_between.lower.year,
                "end_date_0": (
                    o.valid_between.upper.day if o.valid_between.upper else ""
                ),
                "end_date_1": (
                    o.valid_between.upper.month if o.valid_between.upper else ""
                ),
                "end_date_2": (
                    o.valid_between.upper.year if o.valid_between.upper else ""
                ),
            }
            for o in self.existing_origins
        ]
        # if we just submitted the form, overwrite initial with submitted data
        # this prevents newly added origin data being cleared if the form does not pass validation
        if self.data.get("submit"):
            new_data = unprefix_formset_data(
                QUOTA_ORIGINS_FORMSET_PREFIX,
                self.data.copy(),
            )
            initial = new_data

        return initial

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

    def clean(self):
        # unprefix origins formset
        submitted_data = unprefix_formset_data(
            QUOTA_ORIGINS_FORMSET_PREFIX,
            self.data.copy(),
        )
        # for each origin, unprefix exclusions formset
        for i, origin_data in enumerate(submitted_data):
            exclusions = unprefix_formset_data(
                QUOTA_EXCLUSIONS_FORMSET_PREFIX,
                origin_data.copy(),
            )
            submitted_data[i]["exclusions"] = exclusions

        self.cleaned_data["origins"] = []

        for i, origin_data in enumerate(submitted_data):
            # instantiate a form per origin data to do validation
            origin_form = QuotaOrderNumberOriginUpdateReactForm(
                data=origin_data,
                initial=origin_data,
                instance=(
                    models.QuotaOrderNumberOrigin.objects.get(pk=origin_data["pk"])
                    if origin_data.get("pk")
                    else None
                ),
            )

            cleaned_exclusions = []

            for exclusion in origin_data["exclusions"]:
                exclusion_form = QuotaOriginExclusionsReactForm(
                    data=exclusion,
                    initial=exclusion,
                )
                if not exclusion_form.is_valid():
                    for field, e in exclusion_form.errors.as_data().items():
                        self.add_extra_error(
                            f"{QUOTA_ORIGINS_FORMSET_PREFIX}-{i}-{field}",
                            e,
                        )
                else:
                    cleaned_exclusions.append(exclusion_form.cleaned_data)

            if not origin_form.is_valid():
                for field, e in origin_form.errors.as_data().items():
                    self.add_extra_error(
                        f"{QUOTA_ORIGINS_FORMSET_PREFIX}-{i}-{field}",
                        e,
                    )
            else:
                origin_form.cleaned_data["exclusions"] = cleaned_exclusions
                self.cleaned_data["origins"].append(origin_form.cleaned_data)

        return super().clean()

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        # CHARLIE REMOVE THIS COMMENT! Edie's hack to provide context for jinja template
        origins_html = render_to_string(
            "includes/quotas/quota-edit-origins.jinja",
            {
                "object": self.instance,
                "request": request,
                "geo_area_options": self.geo_area_options,
                "origins_initial": self.get_origins_initial(),
                "errors": self.errors,
            },
        )

        self.helper.layout = Layout(
            Div(
                Accordion(
                    AccordionSection(
                        "Validity period",
                        "start_date",
                        "end_date",
                    ),
                    AccordionSection(
                        "Category",
                        "category",
                    ),
                    AccordionSection(
                        "Quota origins",
                        Div(
                            HTML(origins_html),
                        ),
                    ),
                ),
                css_class="govuk-width-!-two-thirds",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class QuotaOrderNumberCreateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "order_number",
            "valid_between",
            "category",
            "mechanism",
        ]

    order_number = forms.CharField(
        help_text=ORDER_NUMBER_HELP_TEXT,
        validators=[validators.quota_order_number_validator],
        error_messages={
            "invalid": "Order number must be six digits long and begin with 05",
            "required": "Enter the order number",
        },
    )
    category = forms.ChoiceField(
        choices=validators.QuotaCategory.choices,
        help_text=CATEGORY_HELP_TEXT,
        error_messages={
            "invalid_choice": "Please select a valid category",
            "required": "Choose the category",
        },
    )
    mechanism = forms.ChoiceField(
        choices=validators.AdministrationMechanism.choices,
        error_messages={
            "invalid_choice": "Please select a valid mechanism",
            "required": "Choose the mechanism",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["start_date"].help_text = START_DATE_HELP_TEXT

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Accordion(
                AccordionSection(
                    "Order number",
                    "order_number",
                ),
                AccordionSection(
                    "Validity",
                    "start_date",
                    "end_date",
                ),
                AccordionSection(
                    "Category and mechanism",
                    "category",
                    "mechanism",
                ),
                css_class="govuk-width-!-two-thirds",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        category = self.cleaned_data.get("category")
        mechanism = self.cleaned_data.get("mechanism")
        order_number = self.cleaned_data.get("order_number", "")

        if (
            mechanism is not None
            and int(mechanism) == validators.AdministrationMechanism.LICENSED
        ):
            if int(category) == validators.QuotaCategory.SAFEGUARD:
                raise ValidationError(
                    "Mechanism cannot be set to licensed for safeguard quotas",
                )
            if not order_number.startswith("054"):
                raise ValidationError(
                    "The order number for licensed quotas must begin with 054",
                )

        if (
            category is not None
            and int(
                category,
            )
            == validators.QuotaCategory.SAFEGUARD
            and not order_number.startswith("058")
        ):
            raise ValidationError(
                "The order number for safeguard quotas must begin with 058",
            )

        return super().clean()


class QuotaOrderNumberOriginForm(
    FormSetSubmitMixin,
    ValidityPeriodForm,
    BindNestedFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaOrderNumberOrigin
        fields = [
            "valid_between",
            "geographical_area",
        ]

    geographical_area = forms.ModelChoiceField(
        label="Geographical area",
        help_text="Add a geographical area",
        queryset=GeographicalArea.objects.all(),
    )

    exclusions = FormSetField(
        label="Geographical area exclusions",
        nested_forms=[QuotaOriginExclusionsFormSet],
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.set_initial_data(*args, **kwargs)
        self.init_layout()

    def set_initial_data(self, *args, **kwargs):
        kwargs.pop("instance")
        self.bind_nested_forms(*args, **kwargs)

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                "start_date",
                "end_date",
                "geographical_area",
                "exclusions",
                css_class="govuk-!-width-two-thirds",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def init_fields(self):
        self.fields["geographical_area"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .prefetch_related("descriptions")
            .order_by("description")
        )
        self.fields["geographical_area"].label_from_instance = (
            lambda obj: f"{obj.area_id} - {obj.description}"
        )


class QuotaDefinitionUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaDefinition
        fields = [
            "valid_between",
            "description",
            "volume",
            "initial_volume",
            "measurement_unit",
            "measurement_unit_qualifier",
            "quota_critical_threshold",
            "quota_critical",
        ]

    description = forms.CharField(label="", widget=forms.Textarea(), required=False)
    volume = forms.DecimalField(
        label="Current volume",
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Volume must be a number",
            "required": "Enter the volume",
        },
    )
    initial_volume = forms.DecimalField(
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Initial volume must be a number",
            "required": "Enter the initial volume",
        },
    )
    measurement_unit = forms.ModelChoiceField(
        queryset=MeasurementUnit.objects.current(),
        error_messages={"required": "Select the measurement unit"},
    )
    quota_critical_threshold = forms.DecimalField(
        label="Threshold",
        help_text="The point at which this quota definition period becomes critical, as a percentage of the total volume.",
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Critical threshold must be a number",
            "required": "Enter the critical threshold",
        },
    )
    quota_critical = forms.TypedChoiceField(
        label="Is the quota definition period in a critical state?",
        help_text="This determines if a trader needs to pay securities when utilising the quota.",
        coerce=lambda value: value == "True",
        choices=((True, "Yes"), (False, "No")),
        widget=forms.RadioSelect(),
        error_messages={"required": "Critical state must be set"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()
        self.init_fields()

    def clean(self):
        validators.validate_quota_volume(self.cleaned_data)
        return super().clean()

    def init_fields(self):
        self.fields["measurement_unit"].queryset = self.fields[
            "measurement_unit"
        ].queryset.order_by("code")
        self.fields["measurement_unit"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.description}"
        )

        self.fields["measurement_unit_qualifier"].queryset = self.fields[
            "measurement_unit_qualifier"
        ].queryset.order_by("code")
        self.fields["measurement_unit_qualifier"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.description}"
        )

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Accordion(
                AccordionSection(
                    "Description",
                    "description",
                ),
                AccordionSection(
                    "Validity period",
                    "start_date",
                    "end_date",
                ),
                AccordionSection(
                    "Measurements",
                    Field("measurement_unit", css_class="govuk-!-width-full"),
                    Field("measurement_unit_qualifier", css_class="govuk-!-width-full"),
                ),
                AccordionSection(
                    "Volume",
                    "initial_volume",
                    "volume",
                ),
                AccordionSection(
                    "Criticality",
                    "quota_critical_threshold",
                    "quota_critical",
                ),
                css_class="govuk-!-width-two-thirds",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class QuotaDefinitionCreateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = models.QuotaDefinition
        fields = [
            "valid_between",
            "description",
            "volume",
            "initial_volume",
            "measurement_unit",
            "measurement_unit_qualifier",
            "quota_critical_threshold",
            "quota_critical",
            "maximum_precision",
        ]

    description = forms.CharField(label="", widget=forms.Textarea(), required=False)
    volume = forms.DecimalField(
        label="Current volume",
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Volume must be a number",
            "required": "Enter the volume",
        },
    )
    initial_volume = forms.DecimalField(
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Initial volume must be a number",
            "required": "Enter the initial volume",
        },
    )
    measurement_unit = forms.ModelChoiceField(
        queryset=MeasurementUnit.objects.current(),
        error_messages={"required": "Select the measurement unit"},
    )

    quota_critical_threshold = forms.DecimalField(
        label="Threshold",
        help_text="The point at which this quota definition period becomes critical, as a percentage of the total volume.",
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Critical threshold must be a number",
            "required": "Enter the critical threshold",
        },
    )
    quota_critical = forms.TypedChoiceField(
        label="Is the quota definition period in a critical state?",
        help_text="This determines if a trader needs to pay securities when utilising the quota.",
        coerce=lambda value: value == "True",
        choices=((True, "Yes"), (False, "No")),
        widget=forms.RadioSelect(),
        error_messages={"required": "Critical state must be set"},
    )
    maximum_precision = forms.IntegerField(
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_layout()
        self.init_fields()

    def clean(self):
        validators.validate_quota_volume(self.cleaned_data)
        return super().clean()

    def init_fields(self):
        # This is always set to 3 for current definitions
        # see https://uktrade.github.io/tariff-data-manual/documentation/data-structures/quotas.html#the-quota-definition-table
        self.fields["maximum_precision"].initial = 3

        # Set these as the default values
        self.fields["quota_critical"].initial = False
        self.fields["quota_critical_threshold"].initial = 90

        self.fields["measurement_unit"].queryset = self.fields[
            "measurement_unit"
        ].queryset.order_by("code")
        self.fields["measurement_unit"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.description}"
        )

        self.fields["measurement_unit_qualifier"].queryset = self.fields[
            "measurement_unit_qualifier"
        ].queryset.order_by("code")
        self.fields["measurement_unit_qualifier"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.description}"
        )

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Accordion(
                AccordionSection(
                    "Description",
                    HTML.p("Adding a description is optional."),
                    "description",
                    "order_number",
                ),
                AccordionSection(
                    "Validity period",
                    "start_date",
                    "end_date",
                ),
                AccordionSection(
                    "Measurements",
                    HTML.p("A measurement unit qualifier is not always required."),
                    Field("measurement_unit", css_class="govuk-!-width-full"),
                    Field("measurement_unit_qualifier", css_class="govuk-!-width-full"),
                ),
                AccordionSection(
                    "Volume",
                    HTML.p(
                        "The initial volume is the legal balance applied to the definition period.<br><br>The current volume is the starting balance for the quota.",
                    ),
                    "initial_volume",
                    "volume",
                    "maximum_precision",
                ),
                AccordionSection(
                    "Criticality",
                    "quota_critical_threshold",
                    "quota_critical",
                ),
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class QuotaOrderNumberOriginUpdateForm(
    QuotaOrderNumberOriginForm,
):
    def set_initial_data(self, *args, **kwargs):
        nested_forms_initial = {**self.initial}
        nested_forms_initial.update(self.get_geo_area_initial())
        kwargs.pop("initial")
        self.bind_nested_forms(*args, initial=nested_forms_initial, **kwargs)

    def get_geo_area_initial(self):
        field_name = "exclusion"
        initial = {}
        initial_exclusions = []
        if self.instance.pk:
            initial_exclusions = [
                {field_name: exclusion.excluded_geographical_area}
                for exclusion in self.instance.quotaordernumberoriginexclusion_set.current()
            ]
        # if we just submitted the form, add the new data to initial
        if self.formset_submitted or self.whole_form_submit:
            new_data = unprefix_formset_data(
                QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX,
                self.data.copy(),
            )
            for g in new_data:
                if g[field_name]:
                    id = int(g[field_name])
                    g[field_name] = GeographicalArea.objects.get(id=id)
            initial_exclusions = new_data

        initial[QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX] = initial_exclusions

        return initial


class QuotaOrderNumberOriginUpdateReactForm(QuotaOrderNumberOriginUpdateForm):
    """Used only to validate data sent from the quota edit React form."""

    pk = forms.IntegerField(required=False)


class QuotaOriginExclusionsReactForm(forms.Form):
    """Used only to validate data sent from the quota edit React form."""

    pk = forms.IntegerField(required=False)
    # field name is different to match the react form
    geographical_area = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),
        help_text="Select a country to be excluded:",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["geographical_area"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )


class QuotaSuspensionType(TextChoices):
    SUSPENSION = "SUSPENSION", "Suspension period"
    BLOCKING = "BLOCKING", "Blocking period"


class BlockingPeriodTypeForm(forms.Form):
    blocking_period_type = forms.ChoiceField(
        help_text="Select a blocking period type.",
        choices=validators.BlockingPeriodType.choices,
        error_messages={
            "required": "Select a blocking period type",
        },
    )


class QuotaSuspensionOrBlockingCreateForm(
    ValidityPeriodBaseForm,
    BindNestedFormMixin,
    forms.Form,
):
    quota_definition = forms.ModelChoiceField(
        label="Quota definition SID",
        empty_label="Select a quota definition SID",
        queryset=models.QuotaDefinition.objects.all(),
        error_messages={
            "required": "Select a quota definition SID",
        },
    )

    suspension_type = RadioNested(
        label="Do you want to create a suspension or blocking period?",
        help_text="Select one option.",
        choices=QuotaSuspensionType.choices,
        nested_forms={
            QuotaSuspensionType.SUSPENSION.value: [],
            QuotaSuspensionType.BLOCKING.value: [BlockingPeriodTypeForm],
        },
        error_messages={
            "required": "Select if you want to create a suspension or blocking period",
        },
    )

    description = forms.CharField(
        label="Description",
        validators=[SymbolValidator],
        widget=forms.Textarea(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.quota_order_number = kwargs.pop("quota_order_number")
        super().__init__(*args, **kwargs)
        self.bind_nested_forms(*args, **kwargs)
        self.init_fields()
        self.init_layout()

    def init_fields(self):
        self.fields["quota_definition"].queryset = (
            models.QuotaDefinition.objects.current()
            .as_at_today_and_beyond()
            .filter(order_number=self.quota_order_number)
            .order_by("-sid")
        )
        self.fields["quota_definition"].label_from_instance = (
            lambda obj: f"{obj.sid} ({obj.valid_between.lower} - {obj.valid_between.upper})"
        )

    def init_layout(self):
        cancel_url = reverse_lazy(
            "quota-ui-detail",
            kwargs={"sid": self.quota_order_number.sid},
        )
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "quota_definition",
            "suspension_type",
            Field.textarea("description", rows=5),
            "start_date",
            "end_date",
            Div(
                Submit(
                    "submit",
                    "Save",
                    css_class="govuk-button--primary",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
                HTML(
                    f"<a class='govuk-button govuk-button--secondary' href={cancel_url}>Cancel</a>",
                ),
                css_class="govuk-button-group",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        definition_period = (
            cleaned_data["quota_definition"].valid_between
            if cleaned_data.get("quota_definition")
            else None
        )
        validity_period = cleaned_data.get("valid_between")
        if (
            definition_period
            and validity_period
            and not validity_range_contains_range(definition_period, validity_period)
        ):
            raise ValidationError(
                f"The start and end date must sit within the selected quota definition's start and end date ({definition_period.lower} - {definition_period.upper})",
            )

        return cleaned_data

    def save(self, workbasket):
        type_to_create_map = {
            QuotaSuspensionType.SUSPENSION: self.create_suspension_period,
            QuotaSuspensionType.BLOCKING: self.create_blocking_period,
        }
        create_object = type_to_create_map.get(self.cleaned_data["suspension_type"])
        return create_object(workbasket=workbasket)

    def create_suspension_period(self, workbasket):
        return models.QuotaSuspension.objects.create(
            quota_definition=self.cleaned_data["quota_definition"],
            description=self.cleaned_data["description"],
            valid_between=self.cleaned_data["valid_between"],
            update_type=UpdateType.CREATE,
            transaction=workbasket.new_transaction(),
        )

    def create_blocking_period(self, workbasket):
        return models.QuotaBlocking.objects.create(
            quota_definition=self.cleaned_data["quota_definition"],
            blocking_period_type=self.cleaned_data["blocking_period_type"],
            description=self.cleaned_data["description"],
            valid_between=self.cleaned_data["valid_between"],
            update_type=UpdateType.CREATE,
            transaction=workbasket.new_transaction(),
        )


class DuplicateQuotaDefinitionPeriodStartForm(forms.Form):
    pass


class QuotaOrderNumersSelectForm(forms.Form):
    class Meta:
        fields = [
            "parent_quota_order_number",
            "child_quota_order_number",
        ]
    parent_quota_order_number = AutoCompleteField(
            label="Parent quota order number",
            queryset=models.QuotaOrderNumber.objects.all(),
            required=True,
        )
    child_quota_order_number = AutoCompleteField(
            label="Child quota order number",
            queryset=models.QuotaOrderNumber.objects.all(),
            required=True,
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.init_layout(self.request)

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                "parent_quota_order_number",
                "child_quota_order_number",
            ),
            Submit(
                "submit",
                "Save and continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        # returns the child and parent OrderNumber objects
        # if we're going to create asynchronously (arguably, even if we're not), we should just return the OrderNumber SIDs
        cleaned_data["parent_quota_order_number"] = self.cleaned_data.get('parent_quota_order_number')
        cleaned_data["child_quota_order_number"] = self.cleaned_data.get('child_quota_order_number')
        return cleaned_data


class SelectSubQuotaDefinitionsForm(
    SelectableObjectsForm,
):
    def clean(self):
        cleaned_data = super().clean()
        selected_definitions = {key: value for key, value in cleaned_data.items() if value}
        definitions_pks = [self.object_id_from_field_name(key) for key in selected_definitions]

        selected_definitions = models.QuotaDefinition.objects.filter(pk__in=definitions_pks).current()
        cleaned_data["selected_definitions"] = selected_definitions
        return cleaned_data


class SelectedDefinitionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.objects = kwargs.pop("objects", [])
        print('*'*30, f"SelectedDefinitionsForm {self.objects}")
        super().__init__(*args, **kwargs)

    def clean(self):
        print('*'*30,'SelectedDefinitionsForm, clean')
        cleaned_data = super().clean()
        # TODO: check that each definition has a coefficient and association
        cleaned_data['duplicated_definitions'] = self.objects
        print('*'*30, f'{cleaned_data=}')
        return cleaned_data

    def save(self):
        # Save the new data
        # create the association
        pass


class SubQuotaDefinitionsUpdatesForm(
    ValidityPeriodForm,
):
    class Meta:
        model = models.QuotaDefinition
        fields = [
            "coefficient",
            "relationship_type",
            "volume",
            "measurement_unit",
        ]

    relationship_type = forms.ChoiceField(
        choices=[
            ("EQ", "Equivalent"),
            ("NM", "Normal"),
        ],
        help_text=RELATIONSHIP_TYPE_HELP_TEXT,
        error_messages={
            "required": "Choose the category",
        },
    )

    coefficient = forms.DecimalField(
        label="Coefficient",
        widget=forms.TextInput(),
        help_text=COEFFICIENT_HELP_TEXT,
        error_messages={
            "invalid": "Coefficient must be a number",
            "required": "Enter the volume",
        },
    )

    volume = forms.DecimalField(
        label="Volume",
        widget=forms.TextInput(),
        error_messages={
            "invalid": "Volume must be a number",
            "required": "Enter the volume",
        },
    )

    measurement_unit = forms.ModelChoiceField(
        queryset=MeasurementUnit.objects.current(),
        error_messages={"required": "Select the measurement unit"},
    )

    def get_duplicate_data(self, main_def_id):
        original_definition = models.QuotaDefinition.objects.get(trackedmodel_ptr_id=main_def_id)
        # models.QuotaDefinition.objects.current()
        #     .as_at_today_and_beyond()
        #     .filter(order_number=self.quota_order_number)
            # .order_by("-sid")
        duplicate_data = models.QuotaDefinitionDuplicator.objects.get(parent_definition_id=original_definition).definition_data
        self.set_initial_data(duplicate_data)
        return duplicate_data

    def set_initial_data(self, duplicate_data):
        print('*'*30, 'set_initial_data' f'{duplicate_data=}')
        fields = self.fields
        fields['measurement_unit'].initial = MeasurementUnit.objects.get(code=duplicate_data['measurement_unit'])
        fields['volume'].initial = duplicate_data['volume']
        fields['start_date'].initial = deserialize_date(duplicate_data['start_date'])
        fields['end_date'].initial = deserialize_date(duplicate_data['end_date'])

    def init_fields(self):
        self.fields["measurement_unit"].queryset = self.fields[
            "measurement_unit"
        ].queryset.order_by("code")
        self.fields["measurement_unit"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.description}"
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        main_def_id = kwargs.pop("sid")
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.get_duplicate_data(main_def_id)
        self.init_layout(self.request)

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        # TODO: add padding to headers to bring them inline with the main body
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Quota association details</h3>',
                    ),
                    Div("relationship_type", css_class="govuk-grid-column-one-half"),
                    Div("coefficient", css_class="govuk-grid-column-one-half"),
                    css_class="govuk-grid-row",
                ),
            ),
            HTML(
                    '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Sub quota definition details</h3>',
                    ),
                    Div(
                        "start_date",
                        css_class="govuk-grid-column-one-half",
                    ),
                    Div(
                        "end_date",
                        css_class="govuk-grid-column-one-half",
                    ),
                    Div(
                        "volume", css_class="govuk-grid-column-one-half",
                    ),
                    Div(
                        "measurement_unit", css_class="govuk-grid-column-one-half",
                    ),
                    css_class="govuk-grid-row",
                ),
                HTML(
                    '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                ),
                Submit(
                    "submit",
                    "Save and continue",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data['relationship_type'] == 'NM'
            and cleaned_data['coefficient'] != 1
        ):
            raise ValidationError(
                "Where the relationship type is Normal, the coefficient value must be 1",
            )
        if (
            cleaned_data['relationship_type'] == 'EQ'
            and cleaned_data['coefficient'] == 1
        ):
            raise ValidationError(
                "Where the relationship type is Equivalent, the coefficient value must be something other than 1",
            )

        return cleaned_data
