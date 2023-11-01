from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse_lazy

from common.forms import BindNestedFormMixin
from common.forms import FormSet
from common.forms import FormSetField
from common.forms import FormSetSubmitMixin
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.forms import formset_factory
from common.forms import unprefix_formset_data
from geo_areas.models import GeographicalArea
from measures.models import MeasurementUnit
from quotas import models
from quotas import validators
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX

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

        clear_url = reverse_lazy("quota-definitions", kwargs={"sid": object_sid})

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
        self.fields[
            "exclusion"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"


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
        choices=[],  # set in __init__
        error_messages={"invalid_choice": "Please select a valid category"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.set_initial_data(*args, **kwargs)
        self.init_layout()

    def set_initial_data(self, *args, **kwargs):
        self.fields["category"].initial = self.instance.category

    def init_fields(self):
        if self.instance.category == validators.QuotaCategory.SAFEGUARD:
            self.fields["category"].widget = forms.Select(
                attrs={"disabled": True},
                choices=validators.QuotaCategory.choices,
            )
            self.fields["category"].help_text = SAFEGUARD_HELP_TEXT
        else:
            self.fields["category"].choices = validators.QuotaCategoryEditing.choices
            self.fields["category"].help_text = CATEGORY_HELP_TEXT

        self.fields["start_date"].help_text = START_DATE_HELP_TEXT

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        origins_html = render_to_string(
            "includes/quotas/quota-edit-origins.jinja",
            {
                "object": self.instance,
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
        self.fields[
            "geographical_area"
        ].label_from_instance = lambda obj: f"{obj.area_id} - {obj.description}"


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
        self.fields[
            "measurement_unit"
        ].label_from_instance = lambda obj: f"{obj.code} - {obj.description}"

        self.fields["measurement_unit_qualifier"].queryset = self.fields[
            "measurement_unit_qualifier"
        ].queryset.order_by("code")
        self.fields[
            "measurement_unit_qualifier"
        ].label_from_instance = lambda obj: f"{obj.code} - {obj.description}"

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
        self.fields[
            "measurement_unit"
        ].label_from_instance = lambda obj: f"{obj.code} - {obj.description}"

        self.fields["measurement_unit_qualifier"].queryset = self.fields[
            "measurement_unit_qualifier"
        ].queryset.order_by("code")
        self.fields[
            "measurement_unit_qualifier"
        ].label_from_instance = lambda obj: f"{obj.code} - {obj.description}"

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
                        "The initial volume is the legal balance applied to the definition period.<br><br>The current volume is the starting balance for the quota."
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
        if hasattr(self, "instance"):
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
