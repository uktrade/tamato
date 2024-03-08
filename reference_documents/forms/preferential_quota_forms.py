from decimal import Decimal

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import ValidityPeriodForm
from reference_documents.models import PreferentialQuota
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

    def clean_volume(self):
        data = self.cleaned_data["volume"]
        if not data.isdigit():
            raise ValidationError("volume is not valid - it must have a value")
        return Decimal(data)

    def clean_commodity_code(self):
        data = self.cleaned_data["commodity_code"]
        if len(data) != 10 or not data.isdigit():
            raise ValidationError("Commodity Code is not valid - it must be 10 digits")
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
