from crispy_forms_gds.helper import FormHelper

# from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.fields import AutoCompleteField
from common.forms import ValidityPeriodForm
from measures.models import MeasurementUnit
from quotas import models
from quotas import validators
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
    pass


class BulkQuotaDefinitionCreateIntroductoryPeriod(forms.Form):
    pass


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


class BulkQuotaDefinitionCreateSummaryForm:
    pass
