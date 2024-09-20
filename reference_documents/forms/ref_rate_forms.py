from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import DateInputFieldFixed
from common.forms import GovukDateRangeField
from common.forms import ValidityPeriodForm
from common.util import TaricDateRange
from reference_documents.models import RefRate
from reference_documents.validators import commodity_code_validator


class RefRateCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    commodity_code = forms.CharField(
        max_length=10,
        help_text="Enter the 10 digit commodity code",
        validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Enter the commodity code",
        },
    )

    duty_rate = forms.CharField(
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.text(
                "commodity_code",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "duty_rate",
                field_width=Fixed.TEN,
            ),
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = RefRate
        fields = [
            "commodity_code",
            "duty_rate",
            "valid_between",
        ]


class RefRateDeleteForm(forms.ModelForm):
    class Meta:
        model = RefRate
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Submit(
                "submit",
                "Confirm delete",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class RefRateBulkCreateForm(forms.Form):
    commodity_codes = forms.CharField(
        label="Commodity codes",
        widget=forms.Textarea,
        help_text="Enter one or more commodity codes with each one on a new line.",
    )

    duty_rate = forms.CharField(
        validators=[],
        error_messages={
            "invalid": "Duty rate is invalid",
            "required": "Duty rate is required",
        },
    )

    start_date = DateInputFieldFixed(label="Start date")
    end_date = DateInputFieldFixed(
        label="End date",
        required=False,
    )
    valid_between = GovukDateRangeField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.text(
                "commodity_codes",
            ),
            Field.text(
                "duty_rate",
                field_width=Fixed.TEN,
            ),
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        # Clean commodity codes
        commodity_codes = cleaned_data.get("commodity_codes")
        if commodity_codes:
            for commodity_code in commodity_codes.splitlines():
                try:
                    commodity_code_validator(commodity_code)
                except ValidationError:
                    self.add_error(
                        "commodity_codes",
                        "Ensure all commodity codes are 10 digits and each on a new line",
                    )
        # This uses the custom clean method so this form is open to extension for adding multiple duty rates / validity periods in future
        self.custom_clean_validity_period(
            cleaned_data,
            valid_between_field_name="valid_between",
            start_date_field_name="start_date",
            end_date_field_name="end_date",
        )

    def custom_clean_validity_period(
        self,
        cleaned_data,
        valid_between_field_name,
        start_date_field_name,
        end_date_field_name,
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
