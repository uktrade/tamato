from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import ValidityPeriodForm
from reference_documents.models import PreferentialQuota
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.validators import commodity_code_validator
from reference_documents.validators import order_number_validator


class PreferentialQuotaCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = PreferentialQuota
        fields = [
            "quota_order_number",
            "commodity_code",
            "quota_duty_rate",
            "volume",
            "measurement",
            "valid_between",
        ]

    commodity_code = forms.CharField(
        help_text="Commodity Code",
        validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Commodity code is required",
        },
    )

    quota_duty_rate = forms.CharField(
        help_text="Quota Duty Rate",
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    quota_order_number = forms.CharField(
        help_text="Quota Order Number",
        validators=[order_number_validator],
        error_messages={
            "invalid": "Quota Order Number is invalid",
            "required": "Quota Order Number is required",
        },
    )

    volume = forms.CharField(
        help_text="Volume",
        validators=[],
        error_messages={
            "invalid": "Volume invalid",
            "required": "Volume is required",
        },
    )

    measurement = forms.CharField(
        help_text="Measurement",
        validators=[],
        error_messages={
            "invalid": "Measurement invalid",
            "required": "Measurement is required",
        },
    )

    def clean_quota_duty_rate(self):
        data = self.cleaned_data["quota_duty_rate"]
        if len(data) < 1:
            raise ValidationError("Quota duty Rate is not valid - it must have a value")
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "quota_order_number",
            "commodity_code",
            "quota_duty_rate",
            "volume",
            "measurement",
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class PreferentialQuotaBulkCreate(ValidityPeriodForm, forms.ModelForm):
    commodity_codes = forms.CharField(
        label="Commodity codes",
        widget=forms.Textarea,
        # validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Commodity code is required",
        },
    )

    quota_duty_rate = forms.CharField(
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    preferential_quota_order_number = forms.ModelChoiceField(
        help_text="If the quota order number does not appear, you must first create it for this reference document version.",
        queryset=PreferentialQuotaOrderNumber.objects.all(),  # Modified in init
        error_messages={
            "invalid": "Quota Order Number is invalid",
            "required": "Quota Order Number is required",
        },
    )

    volume = forms.CharField(
        validators=[],
        error_messages={
            "invalid": "Volume invalid",
            "required": "Volume is required",
        },
        help_text="<br>",
    )

    measurement = forms.CharField(
        validators=[],
        error_messages={
            "invalid": "Measurement invalid",
            "required": "Measurement is required",
        },
    )

    def __init__(self, reference_document_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferential_quota_order_number"].queryset = (
            PreferentialQuotaOrderNumber.objects.all()
            .filter(reference_document_version=reference_document_version)
            .order_by()
        )
        self.fields[
            "preferential_quota_order_number"
        ].label_from_instance = lambda obj: f"{obj.quota_order_number}"
        self.fields["end_date"].help_text = ""
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "preferential_quota_order_number",
            Field.text(
                "commodity_codes",
            ),
            Field.text(
                "quota_duty_rate",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "measurement",
                field_width=Fixed.TEN,
            ),
            Fieldset(
                Div(
                    Field("start_date"),
                ),
                Div(
                    Field("end_date"),
                ),
                Div(
                    Field(
                        "volume",
                        field_width=Fixed.TEN,
                    ),
                ),
                style="display: grid; grid-template-columns: 2fr 2fr 1fr",
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        commodity_codes = cleaned_data.get("commodity_codes").splitlines()
        for commodity_code in commodity_codes:
            try:
                commodity_code_validator(commodity_code)
            except ValidationError:
                self.add_error(
                    "commodity_codes",
                    "Ensure all commodity codes are 10 digits and each on a new line",
                )

    class Meta:
        model = PreferentialQuota
        fields = [
            "preferential_quota_order_number",
            "quota_duty_rate",
            "measurement",
        ]
