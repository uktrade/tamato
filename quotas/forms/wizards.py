import decimal

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError

from common.fields import AutoCompleteField
from common.forms import ValidityPeriodForm
from common.serializers import deserialize_date
from common.util import TaricDateRange
from common.widgets import DecimalSuffix
from measures.models import MeasurementUnit
from quotas import models
from quotas import validators
from quotas.serializers import serialize_definition_data
from quotas.serializers import serialize_duplicate_data
from workbaskets.forms import SelectableObjectsForm


class DuplicateQuotaDefinitionPeriodStartForm(forms.Form):
    pass


class QuotaOrderNumbersSelectForm(forms.Form):
    main_quota_order_number = AutoCompleteField(
        label="Main quota order number",
        queryset=models.QuotaOrderNumber.objects.all(),
        required=True,
    )
    sub_quota_order_number = AutoCompleteField(
        label="Sub-quota order number",
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
                HTML(
                    '<h2 class="govuk-heading">Enter main and sub-quota order numbers</h2>',
                ),
            ),
            Div(
                "main_quota_order_number",
                Div(
                    "sub_quota_order_number",
                    css_class="govuk-inset-text",
                ),
            ),
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class SelectSubQuotaDefinitionsForm(
    SelectableObjectsForm,
):
    """Form to select the main quota definitions that are to be duplicated."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def set_staged_definition_data(self, selected_definitions):
        if (
            self.prefix in ["select_definition_periods"]
            and self.request.path != "/quotas/duplicate_quota_definitions/complete"
        ):
            staged_definition_data = []
            for definition in selected_definitions:
                staged_definition_data.append(
                    {
                        "main_definition": definition.pk,
                        "sub_definition_staged_data": serialize_duplicate_data(
                            definition,
                        ),
                    },
                )
            self.request.session["staged_definition_data"] = staged_definition_data

    def clean(self):
        cleaned_data = super().clean()
        selected_definitions = {
            key: value for key, value in cleaned_data.items() if value
        }
        definitions_pks = [
            self.object_id_from_field_name(key) for key in selected_definitions
        ]
        if len(selected_definitions) < 1:
            raise ValidationError("At least one quota definition must be selected")
        selected_definitions = models.QuotaDefinition.objects.filter(
            pk__in=definitions_pks,
        ).current()
        cleaned_data["selected_definitions"] = selected_definitions
        self.set_staged_definition_data(selected_definitions)
        return cleaned_data


class SelectedDefinitionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["staged_definitions"] = self.request.session[
            "staged_definition_data"
        ]
        for definition in cleaned_data["staged_definitions"]:
            if not definition["sub_definition_staged_data"]["status"]:
                raise forms.ValidationError(
                    "Each definition period must have a specified relationship and co-efficient value",
                )
        return cleaned_data


class BulkQuotaDefinitionCreateStartForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.init_layout(self.request)

    quota_order_number = AutoCompleteField(
        label="Enter the quota order number",
        queryset=models.QuotaOrderNumber.objects.all(),
        required=True,
    )

    def save_quota_order_number_to_session(self, cleaned_data):
        self.request.session["quota_order_number_pk"] = cleaned_data[
            "quota_order_number"
        ].pk

    def clean(self):
        cleaned_data = super().clean()
        self.save_quota_order_number_to_session(cleaned_data)
        return cleaned_data

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                HTML(
                    '<h2 class="govuk-heading">Enter quota order number</h2>',
                ),
                "quota_order_number",
                Submit(
                    "submit",
                    "Continue",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
            ),
        )


class QuotaDefinitionBulkCreateDefinitionInformation(
    ValidityPeriodForm,
    forms.Form,
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

    instance_count = forms.DecimalField(
        label="Total number of definitions to create",
        widget=forms.TextInput(),
        help_text="You can create up to 20 definition periods at a time per quota order number",
        error_messages={
            "invalid": "Must be a number",
            "required": "Enter the number of definition periods to create",
        },
    )

    frequency = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[
            (1, "Every year"),
            (2, "Every 6 months"),
            (3, "Every 3 months"),
        ],
        help_text="For non-standard frequencies, pick the closest option and edit it on the review page",
    )

    volume = forms.DecimalField(
        label="Current volume",
        widget=DecimalSuffix(),
        help_text="The current volume is the starting balance for the quota",
        error_messages={
            "invalid": "Volume must be a number",
            "required": "Enter the volume",
        },
    )
    initial_volume = forms.DecimalField(
        widget=forms.TextInput(),
        help_text="The initial volume is the legal balance applied to the definition period",
        error_messages={
            "invalid": "Initial volume must be a number",
            "required": "Enter the initial volume",
        },
    )

    measurement_unit = forms.ModelChoiceField(
        empty_label="Choose measurement unit",
        queryset=MeasurementUnit.objects.current(),
        error_messages={"required": "Select the measurement unit"},
    )

    quota_critical_threshold = forms.DecimalField(
        label="Threshold",
        widget=DecimalSuffix(suffix="%"),
        help_text="The point at which this quota definition period becomes critical, as a percentage of the total volume.",
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
    description = forms.CharField(
        label="",
        help_text="Adding a description is optional",
        widget=forms.Textarea(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.init_layout(self.request)
        self.init_fields()

    def init_fields(self):
        # This is always set to 3 for current definitions
        # see https://uktrade.github.io/tariff-data-manual/documentation/data-structures/quotas.html#the-quota-definition-table
        self.fields["maximum_precision"].initial = 3
        self.fields["end_date"].help_text = ""
        self.fields["measurement_unit_qualifier"].help_text = (
            "A measurement unit qualifier is not always required"
        )
        self.fields["measurement_unit_qualifier"].empty_label = (
            "Choose measurement unit qualifier"
        )
        self.fields["quota_critical_threshold"].initial = 90
        self.fields["quota_critical"].initial = False

    def save_definition_data_to_session(self, definition_data):
        recurrance_data = self.request.session["recurrance_data"]
        instance_count = decimal.Decimal(recurrance_data["instance_count"])
        frequency = decimal.Decimal(recurrance_data["frequency"])

        staged_definitions = []
        # definition_data = self.cleaned_data
        definition_data.update(
            {
                "id": 1,
            },
        )
        first_definition = serialize_definition_data(definition_data)
        staged_definitions.append(first_definition)

        while len(staged_definitions) < instance_count:
            id = decimal.Decimal(definition_data["id"]) + 1
            definition_data.update(
                {"id": id},
            )
            """
            There are currently four options for the frequency with which
            definition periods repeat, selected in
            BulkQuotaDefinitionCreateInitialInformation
            1. Annually
            2. Quarterly
            3. Custom
            If the user selects Once the start/end date are entered in the
            following page.
            If the user selects Annually or Quarterly, we calculate the dates
            for the user.
            If the user selects Custom, the initially inputted dates are
            repeated for all definition periods.
            """
            if frequency == 1:
                # Repeats annualy
                new_start_date = definition_data["valid_between"].lower + relativedelta(
                    years=1,
                )
                new_end_date = definition_data["valid_between"].upper + relativedelta(
                    years=1,
                )
                new_date_range = TaricDateRange(
                    new_start_date,
                    new_end_date,
                )
                definition_data.update(
                    {
                        "valid_between": new_date_range,
                    },
                )

            if frequency == 2:
                # Repeats every 6 months
                new_start_date = definition_data["valid_between"].upper + relativedelta(
                    days=1,
                )
                new_end_date = new_start_date + relativedelta(
                    months=6,
                    days=-1,
                )
                new_date_range = TaricDateRange(
                    new_start_date,
                    new_end_date,
                )
                definition_data.update(
                    {"valid_between": new_date_range},
                )
            if frequency == 3:
                # repeats quarterly
                new_start_date = definition_data["valid_between.upper"] + relativedelta(
                    days=1,
                )
                new_end_date = new_start_date + relativedelta(
                    months=3,
                    days=-1,
                )
                new_date_range = TaricDateRange(
                    new_start_date,
                    new_end_date,
                )
                definition_data.update(
                    {"valid_between": new_date_range},
                )
            # TODO: Add option for incremental/decremental changes to volume
            serialized_definition_data = serialize_definition_data(definition_data)
            staged_definitions.append(serialized_definition_data)

        self.request.session["staged_definition_data"] = staged_definitions

    def clean(self):
        cleaned_data = super().clean()
        self.save_definition_data_to_session(definition_data=cleaned_data)
        return cleaned_data

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                HTML(
                    '<h2 class="govuk-heading">First definition period</h2>',
                ),
                Div(
                    HTML(
                        '<p class="govuk-body">Enter the dates for the first definition period you are creating. Subsequent definition period dates will be calculated based on the dates entered for this first period</p>',
                    ),
                    "start_date",
                    "end_date",
                ),
                Div(
                    HTML(
                        '<h2 class="govuk-heading">Subsequent definition periods</h2>',
                    ),
                ),
                Div(
                    HTML(
                        '<p class="govuk-body">Select the frequency at which the subsequent definition periods should be duplicated</p>',
                    ),
                    "frequency",
                    Field(
                        "instance_count",
                        css_class="govuk-input govuk-input--width-2",
                    ),
                ),
                HTML(
                    '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Measurements</h3>',
                    ),
                    Field("measurement_unit", css_class="govuk-!-width-two-thirds"),
                    Field(
                        "measurement_unit_qualifier",
                        css_class="govuk-!-width-two-thirds",
                    ),
                ),
                HTML(
                    "<br />",
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Volume</h3>',
                    ),
                    HTML.p(
                        "The initial volume is the legal balance applied to the definition period.<br><br>The current volume is the starting balance for the quota.",
                    ),
                    Field("initial_volume", css_class="govuk-!-width-one-third"),
                    Field("volume", css_class="govuk-!-width-one-third"),
                    "maximum_precision",
                ),
                HTML(
                    "<br />",
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Criticality</h3>',
                    ),
                    Field(
                        "quota_critical_threshold",
                        css_class="govuk-!-width-two-thirds",
                    ),
                    "quota_critical",
                ),
                HTML(
                    "<br />",
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Description</h3>',
                    ),
                    Field("description", css_class="govuk-!-width-two-thirds"),
                ),
                Submit(
                    "submit",
                    "Next",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
            ),
        )


class BulkQuotaDefinitionCreateReviewForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)


# TODO: Investigate extending QuotaDefinitionCreateForm here
class BulkDefinitionUpdateData(
    ValidityPeriodForm,
    forms.Form,
):
    """This is broadly similar to the QuotaDefinitionCreateForm."""

    class Meta:
        model = models.QuotaDefinition
        fields = [
            "valid_between",
            "description",
            "volume",
            "initial_volume",
            "measurement_unit",
            "quota_critical_threshold",
            "quota_critical",
            "maximum_precision",
        ]

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
        self.request = kwargs.pop("request")
        self.definition_data = self.request.session["staged_definition_data"][
            int(kwargs.pop("pk")) - 1
        ]
        super().__init__(*args, **kwargs)
        self.init_layout(self.request)
        self.init_fields()

    def init_fields(self):
        fields = self.fields
        definition_data = self.definition_data
        # This is always set to 3 for current definitions
        # see https://uktrade.github.io/tariff-data-manual/documentation/data-structures/quotas.html#the-quota-definition-table
        fields["maximum_precision"].initial = 3
        fields["start_date"].initial = deserialize_date(definition_data["start_date"])
        fields["end_date"].initial = deserialize_date(definition_data["end_date"])
        fields["initial_volume"].initial = decimal.Decimal(
            definition_data["initial_volume"],
        )
        fields["volume"].initial = decimal.Decimal(definition_data["volume"])
        fields["measurement_unit"].initial = MeasurementUnit.objects.get(
            code=definition_data["measurement_unit_code"],
        )
        fields["quota_critical_threshold"].initial = decimal.Decimal(
            definition_data["threshold"],
        )
        fields["quota_critical"].initial = definition_data["quota_critical"]

    def update_definition_data_in_session(self, cleaned_data):
        cleaned_data.update(
            {
                "id": self.definition_data["id"],
            },
        )
        serialized_clean_data = serialize_definition_data(cleaned_data)
        self.request.session["staged_definition_data"][
            int(serialized_clean_data["id"]) - 1
        ].update(serialized_clean_data)

    def clean(self):
        cleaned_data = super().clean()
        self.update_definition_data_in_session(cleaned_data)

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                HTML(
                    '<h2 class="govuk-heading">Enter base definition information</h2>',
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Validity period</h3>',
                    ),
                    "start_date",
                    "end_date",
                ),
                HTML(
                    '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Measurements</h3>',
                    ),
                    HTML.p("A measurement unit qualifier is not always required."),
                    Field("measurement_unit", css_class="govuk-!-width-full"),
                    # Field("measurement_unit_qualifier", css_class="govuk-!-width-full"),
                ),
                HTML(
                    '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Volume</h3>',
                    ),
                    HTML.p(
                        "The initial volume is the legal balance applied to the definition period.<br><br>The current volume is the starting balance for the quota.",
                    ),
                    "initial_volume",
                    "volume",
                    "maximum_precision",
                ),
                HTML(
                    '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                ),
                Div(
                    HTML(
                        '<h3 class="govuk-heading">Criticality</h3>',
                    ),
                    "quota_critical_threshold",
                    "quota_critical",
                ),
                Submit(
                    "submit",
                    "Next",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                ),
            ),
        )


# This is the current form. Leave as is for now
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
            Div(
                HTML(
                    '<h3 class="govuk-heading">Definitions count</h3>',
                ),
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                HTML(
                    '<h3 class="govuk-heading">Description</h3>',
                ),
                HTML.p("Adding a description is optional."),
                "description",
                "order_number",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                HTML(
                    '<h3 class="govuk-heading">Validity period</h3>',
                ),
                "start_date",
                "end_date",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                HTML(
                    '<h3 class="govuk-heading">Measurements</h3>',
                ),
                HTML.p("A measurement unit qualifier is not always required."),
                Field("measurement_unit", css_class="govuk-!-width-full"),
                Field("measurement_unit_qualifier", css_class="govuk-!-width-full"),
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                HTML(
                    '<h3 class="govuk-heading">Volume</h3>',
                ),
                HTML.p(
                    "The initial volume is the legal balance applied to the definition period.<br><br>The current volume is the starting balance for the quota.",
                ),
                "initial_volume",
                "volume",
                "maximum_precision",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                HTML(
                    '<h3 class="govuk-heading">Criticality</h3>',
                ),
                "quota_critical_threshold",
                "quota_critical",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )
