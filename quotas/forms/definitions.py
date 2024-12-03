from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import ValidityPeriodForm
from common.serializers import deserialize_date
from common.widgets import DecimalSuffix
from measures.models import MeasurementUnit
from quotas import business_rules
from quotas import models
from quotas import validators
from quotas.constants import COEFFICIENT_HELP_TEXT
from quotas.constants import RELATIONSHIP_TYPE_HELP_TEXT
from workbaskets.models import WorkBasket


class QuotaDefinitionMixin:
    model = models.QuotaDefinition

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaDefinition.objects.approved_up_to_transaction(tx)


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
        help_text="The current volume is the starting balance for the quota",
        widget=forms.TextInput(),
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
        queryset=MeasurementUnit.objects.current(),
        empty_label="Choose measurement unit",
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

        self.fields["end_date"].help_text = ""
        self.fields["measurement_unit_qualifier"].help_text = (
            "A measurement unit qualifier is not always required."
        )
        self.fields["measurement_unit_qualifier"].empty_label = (
            "Choose measurement unit qualifier."
        )

    def init_layout(self, *args, **kwargs):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                HTML(
                    '<h3 class="govuk-heading">Validity period</h3>',
                ),
                "start_date",
                "end_date",
            ),
            HTML(
                "<br />",
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
                "quota_critical_threshold",
                "quota_critical",
            ),
            HTML(
                "<br />",
            ),
            Div(
                HTML(
                    '<h3 class="govuk-heading">Description</h3>',
                ),
                HTML.p("Adding a description is optional."),
                "description",
            ),
            HTML(
                "<br />",
            ),
            Submit(
                "submit",
                "Submit",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class SubQuotaDefinitionsUpdatesForm(
    ValidityPeriodForm,
):
    """Form used to edit duplicated sub-quota definitions and associations as
    part of the sub-quota create journey."""

    class Meta:
        model = models.QuotaDefinition
        fields = [
            "coefficient",
            "relationship_type",
            "volume",
            "initial_volume",
            "measurement_unit",
            "valid_between",
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
            "required": "Enter the coefficient",
        },
    )

    initial_volume = forms.DecimalField(
        label="Initial volume",
        widget=forms.TextInput(),
        help_text="The initial volume is the legal balance applied to the definition period.",
        error_messages={
            "invalid": "Initial volume must be a number",
            "required": "Enter the initial volume",
        },
    )
    volume = forms.DecimalField(
        label="Current volume",
        widget=forms.TextInput(),
        help_text="The current volume is the starting balance for the quota.",
        error_messages={
            "invalid": "Volume must be a number",
            "required": "Enter the volume",
        },
    )

    measurement_unit = forms.ModelChoiceField(
        label="Measurement unit",
        queryset=MeasurementUnit.objects.current().order_by("code"),
        error_messages={"required": "Select the measurement unit"},
    )

    def get_duplicate_data(self, original_definition):
        staged_definition_data = self.request.session["staged_definition_data"]
        duplicate_data = list(
            filter(
                lambda staged_definition_data: staged_definition_data["main_definition"]
                == original_definition.pk,
                staged_definition_data,
            ),
        )[0]["sub_definition_staged_data"]
        self.set_initial_data(duplicate_data)
        return duplicate_data

    def set_initial_data(self, duplicate_data):
        fields = self.fields
        fields["relationship_type"].initial = "NM"
        fields["coefficient"].initial = 1
        fields["measurement_unit"].initial = MeasurementUnit.objects.get(
            code=duplicate_data["measurement_unit_code"],
        )
        fields["initial_volume"].initial = duplicate_data["initial_volume"]
        fields["volume"].initial = duplicate_data["volume"]
        fields["start_date"].initial = deserialize_date(duplicate_data["start_date"])
        fields["end_date"].initial = deserialize_date(duplicate_data["end_date"])

    def init_fields(self):
        self.fields["measurement_unit"].label_from_instance = (
            lambda obj: f"{obj.code} - {obj.description}"
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        main_def_id = kwargs.pop("pk")
        super().__init__(*args, **kwargs)
        self.original_definition = models.QuotaDefinition.objects.get(
            trackedmodel_ptr_id=main_def_id,
        )
        self.init_fields()
        self.get_duplicate_data(self.original_definition)
        self.init_layout(self.request)

    def clean(self):
        cleaned_data = super().clean()
        """
        Carrying out business rule checks here to prevent erroneous
        associations, see:

        https://uktrade.github.io/tariff-data-manual/documentation/data-structures/quota-associations.html#validation-rules
        """
        original_definition = self.original_definition
        if cleaned_data["valid_between"].upper is None:
            raise ValidationError("An end date must be supplied")

        if not business_rules.check_QA2_dict(
            sub_definition_valid_between=cleaned_data["valid_between"],
            main_definition_valid_between=original_definition.valid_between,
        ):
            raise ValidationError(
                "QA2: Validity period for sub-quota must be within the "
                "validity period of the main quota",
            )

        if not business_rules.check_QA3_dict(
            main_definition_unit=self.original_definition.measurement_unit,
            sub_definition_unit=cleaned_data["measurement_unit"],
            main_definition_volume=original_definition.volume,
            sub_definition_volume=cleaned_data["volume"],
            main_initial_volume=original_definition.initial_volume,
            sub_initial_volume=cleaned_data["initial_volume"],
        ):
            raise ValidationError(
                "QA3: When converted to the measurement unit of the main "
                "quota, the volume of a sub-quota must always be lower than "
                "or equal to the volume of the main quota",
            )

        if not business_rules.check_QA4_dict(cleaned_data["coefficient"]):
            raise ValidationError(
                "QA4: A coefficient must be a positive decimal number",
            )

        if cleaned_data["relationship_type"] == "NM":
            if not business_rules.check_QA5_normal_coefficient(
                cleaned_data["coefficient"],
            ):
                raise ValidationError(
                    "QA5: Where the relationship type is Normal, the "
                    "coefficient value must be 1",
                )
        elif cleaned_data["relationship_type"] == "EQ":
            if not business_rules.check_QA5_equivalent_coefficient(
                cleaned_data["coefficient"],
            ):
                raise ValidationError(
                    "QA5: Where the relationship type is Equivalent, the "
                    "coefficient value must be something other than 1",
                )
            if not business_rules.check_QA5_equivalent_volumes(
                self.original_definition,
                volume=cleaned_data["volume"],
            ):
                raise ValidationError(
                    "Whenever a sub-quota is defined with the 'equivalent' "
                    "type, it must have the same volume as the ones associated"
                    " with the parent quota",
                )

        if not business_rules.check_QA6_dict(
            main_quota=original_definition,
            new_relation_type=cleaned_data["relationship_type"],
        ):
            ValidationError(
                "QA6: Sub-quotas associated with the same main quota must "
                "have the same relation type.",
            )

        return cleaned_data

    def init_layout(self, request):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Div(
                HTML(
                    '<h2 class="govuk-heading">Quota association details</h2>',
                ),
                Div(
                    Div("relationship_type", css_class="govuk-grid-column-one-half"),
                    Div("coefficient", css_class="govuk-grid-column-one-half"),
                    css_class="govuk-grid-row",
                ),
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                HTML(
                    '<h2 class="govuk-heading">Sub-quota definition details</h2>',
                ),
                Div(
                    Div(
                        "start_date",
                        css_class="govuk-grid-column-one-half",
                    ),
                    Div(
                        "end_date",
                        css_class="govuk-grid-column-one-half",
                    ),
                    Div(
                        "initial_volume",
                        "measurement_unit",
                        css_class="govuk-grid-column-one-half",
                    ),
                    Div(
                        "volume",
                        css_class="govuk-grid-column-one-half",
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


class SubQuotaDefinitionAssociationUpdateForm(SubQuotaDefinitionsUpdatesForm):
    """Form used to update sub-quota definitions and associations as part of the
    edit sub-quotas journey."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.workbasket = self.request.user.current_workbasket
        sub_quota_definition_sid = kwargs.pop("sid")
        ValidityPeriodForm.__init__(self, *args, **kwargs)
        self.sub_quota = models.QuotaDefinition.objects.current().get(
            sid=sub_quota_definition_sid,
        )
        self.init_fields()
        self.set_initial_data()
        self.init_layout(self.request)

    def set_initial_data(self):
        association = models.QuotaAssociation.objects.current().get(
            sub_quota__sid=self.sub_quota.sid,
        )
        self.original_definition = association.main_quota
        fields = self.fields
        fields["relationship_type"].initial = association.sub_quota_relation_type
        fields["coefficient"].initial = association.coefficient
        fields["measurement_unit"].initial = self.sub_quota.measurement_unit
        fields["initial_volume"].initial = self.sub_quota.initial_volume
        fields["volume"].initial = self.sub_quota.volume
        fields["start_date"].initial = self.sub_quota.valid_between.lower
        fields["end_date"].initial = self.sub_quota.valid_between.upper

    def init_fields(self):
        super().init_fields()
        if self.sub_quota.valid_between.lower <= date.today():
            self.fields["coefficient"].disabled = True
            self.fields["relationship_type"].disabled = True
            self.fields["start_date"].disabled = True
            self.fields["initial_volume"].disabled = True
            self.fields["volume"].disabled = True
            self.fields["measurement_unit"].disabled = True


class QuotaAssociationUpdateForm(forms.ModelForm):
    class Meta:
        model = models.QuotaAssociation
        fields = [
            "sub_quota_relation_type",
            "coefficient",
            "main_quota",
            "sub_quota",
        ]
