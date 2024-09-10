from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import DateInputFieldFixed
from common.forms import ValidityPeriodForm
from common.util import TaricDateRange
from reference_documents.models import RefQuotaSuspension, RefQuotaDefinition


class RefQuotaSuspensionCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = RefQuotaSuspension
        fields = [
            "ref_quota_definition",
            "valid_between",
        ]

    def __init__(
            self,
            reference_document_version,
            *args,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["ref_quota_definition"].help_text = "The selected quota definition to be suspended"
        self.fields["end_date"].help_text = ''

        self.reference_document_version = reference_document_version

        self.fields["ref_quota_definition"].queryset = (
            RefQuotaDefinition.objects.all().filter(
                ref_order_number__reference_document_version=self.reference_document_version
            ).order_by('ref_order_number__order_number', 'commodity_code')
        )

        # self.preferential_quota = preferential_quota
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "ref_quota_definition",
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean_ref_quota_definition(self):
        error_message = "Quota definition is not valid - it must have a value"

        if "ref_quota_definition" in self.cleaned_data.keys():
            data = self.cleaned_data["ref_quota_definition"]
            if not data:
                raise ValidationError(error_message)
        else:
            raise ValidationError(error_message)

        return data

    def clean(self):
        error_messages = []

        if 'start_date' not in self.cleaned_data.keys():
            self.add_error("start_date", 'Start date is not valid')

        if 'end_date' not in self.cleaned_data.keys():
            self.add_error("end_date", 'End date is not valid')

        if len(self.errors) > 0:
            raise forms.ValidationError(' & '.join(error_messages))

        start_date = self.cleaned_data["start_date"]
        end_date = self.cleaned_data["end_date"]
        ref_quota_definition = self.cleaned_data["ref_quota_definition"]

        if start_date > end_date:
            self.add_error("start_date", 'Start date is after the end date')
            self.add_error("end_date", 'End date is before the start date')
        else:
            self.cleaned_data['valid_between'] = TaricDateRange(start_date, end_date)
            self.instance.valid_between = self.cleaned_data['valid_between']
        if ref_quota_definition.valid_between is None:
            self.add_error("ref_quota_definition", 'Invalid quota definition selected, it has no validity range')
        else:
            if ref_quota_definition.valid_between.lower > start_date:
                self.add_error("start_date", 'Start date is before the quota definitions start date')

            if ref_quota_definition.valid_between.upper < end_date:
                self.add_error("end_date", 'End date is after the quota definitions end date')

        if len(self.errors):
            raise forms.ValidationError(' & '.join(self.errors))

            # This uses the custom clean method so this form is open to extension for adding multiple duty rates / validity periods in future


    ref_quota_definition = forms.ModelChoiceField(
        label="Quota definition",
        help_text="Select the quota definition to be suspended",
        queryset=None,
        validators=[],
        error_messages={
            "invalid": "The selected quota definition is invalid",
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


class RefQuotaSuspensionDeleteForm(forms.Form):
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
        model = RefQuotaSuspension
        fields = []
