from datetime import date

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import DateInputFieldFixed
from common.forms import DateInputFieldTakesParameters
from common.forms import GovukDateRangeField
from common.forms import ValidityPeriodForm
from common.util import TaricDateRange
from reference_documents.models import PreferentialQuotaSuspension, PreferentialQuota
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.validators import commodity_code_validator


class PreferentialQuotaSuspensionCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = PreferentialQuotaSuspension
        fields = [
            "preferential_quota",
            "valid_between",
        ]

    def __init__(
            self,
            reference_document_version,
            *args,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["preferential_quota"].help_text = "The selected quota definition to be suspended"
        self.fields["end_date"].help_text = ''

        self.reference_document_version = reference_document_version

        self.fields["preferential_quota"].queryset = (
            PreferentialQuota.objects.all().filter(
                preferential_quota_order_number__reference_document_version=self.reference_document_version
            ).order_by('preferential_quota_order_number__quota_order_number', 'commodity_code')
        )

        # self.preferential_quota = preferential_quota
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "preferential_quota",
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean_preferential_quota(self):
        error_message = "Preferential quota is not valid - it must have a value"

        if "preferential_quota" in self.cleaned_data.keys():
            data = self.cleaned_data["preferential_quota"]
            if not data:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean(self):
        error_messages = []

        start_date = self.cleaned_data["start_date"]
        end_date = self.cleaned_data["end_date"]
        preferential_quota = self.cleaned_data["preferential_quota"]

        if start_date > end_date:
            self.add_error("start_date", 'Start date is after the end date')
            self.add_error("end_date", 'End date is before the start date')
        else:
            self.cleaned_data['valid_between'] = TaricDateRange(start_date, end_date)
            self.instance.valid_between = self.cleaned_data['valid_between']
        if preferential_quota.valid_between is None:
            self.add_error("preferential_quota", 'Invalid quota definition selected, it has no validity range')
        else:
            if preferential_quota.valid_between.lower > start_date:
                self.add_error("start_date", 'Start date is before the quota definitions start date')

            if preferential_quota.valid_between.upper < end_date:
                self.add_error("end_date", 'End date is after the quota definitions end date')



        if len(error_messages):
            raise forms.ValidationError(' & '.join(error_messages))

            # This uses the custom clean method so this form is open to extension for adding multiple duty rates / validity periods in future


    preferential_quota = forms.ModelChoiceField(
        label="Preferential Quota",
        help_text="Select the preferential quota definition to be suspended",
        queryset=None,
        validators=[],
        error_messages={
            "invalid": "Quota order number is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    start_date = DateInputFieldFixed(
        label="Start date",
    )
    end_date = DateInputFieldFixed(
        label="End date",
    )


class PreferentialQuotaSuspensionDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
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

    class Meta:
        model = PreferentialQuotaSuspension
        fields = []
