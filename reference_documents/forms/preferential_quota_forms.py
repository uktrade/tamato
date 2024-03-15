from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
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

    def __init__(
        self,
        reference_document_version,
        preferential_quota_order_number,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if preferential_quota_order_number:
            self.initial["quota_order_number"] = preferential_quota_order_number

        self.fields[
            "quota_order_number"
        ].queryset = reference_document_version.preferential_quota_order_numbers.all()

        self.reference_document_version = reference_document_version
        self.quota_order_number = preferential_quota_order_number
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "quota_order_number",
            Field.text(
                "commodity_code",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "quota_duty_rate",
                field_width=Fixed.THIRTY,
            ),
            Field.text(
                "volume",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "measurement",
                field_width=Fixed.TWENTY,
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

    def clean_quota_duty_rate(self):
        data = self.cleaned_data["quota_duty_rate"]
        if len(data) < 1:
            raise ValidationError("Quota duty Rate is not valid - it must have a value")
        return data

    # def clean(self, ):
    #     data = self.cleaned_data["quota_duty_rate"]
    #     pass

    # def clean_validity_period(
    #         self,
    #         cleaned_data,
    #         valid_between_field_name="valid_between",
    #         start_date_field_name="start_date",
    #         end_date_field_name="end_date",
    # ):
    #     super().clean_validity_period(cleaned_data, "valid_between", "start_date", "end_date")
    #     print(cleaned_data[valid_between_field_name])
    #     data = self.cleaned_data["quota_duty_rate"]
    #     if data is None:
    #         raise ValidationError("Validity range must have an end date")
    #     return data

    commodity_code = forms.CharField(
        max_length=10,
        help_text="Enter the 10 digit commodity code",
        validators=[commodity_code_validator],
        error_messages={
            "invalid": "Commodity code should be 10 digits",
            "required": "Enter the commodity code",
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

    quota_order_number = forms.ModelChoiceField(
        label="Quota Order Number",
        help_text="Select Quota order number",
        queryset=PreferentialQuotaOrderNumber.objects.all(),
        validators=[],
        error_messages={
            "invalid": "Quota Order number is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
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


class PreferentialQuotaBulkCreate(ValidityPeriodForm, forms.ModelForm):
    commodity_code = forms.CharField(
        validators=[commodity_code_validator],
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
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "preferential_quota_order_number",
            Field.text(
                "commodity_code",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "quota_duty_rate",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "volume",
                field_width=Fixed.TEN,
            ),
            Field.text(
                "measurement",
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
        model = PreferentialQuota
        fields = [
            "preferential_quota_order_number",
            "commodity_code",
            "quota_duty_rate",
            "volume",
            "measurement",
            "valid_between",
        ]


class PreferentialQuotaDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Submit(
                "submit",
                "Confirm Delete",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = PreferentialQuotaOrderNumber
        fields = []
