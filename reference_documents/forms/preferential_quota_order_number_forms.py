from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.forms import ValidityPeriodForm
from reference_documents.models import PreferentialQuotaOrderNumber


class PreferentialQuotaOrderNumberCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = PreferentialQuotaOrderNumber
        fields = [
            "quota_order_number",
            "coefficient",
            "main_order_number",
            "valid_between",
        ]

    quota_order_number = forms.CharField(
        label="Order number",
        help_text="Enter a six digit number",
        validators=[],
        error_messages={
            "invalid": "Quota Order number is invalid",
            "required": "Quota Order number is required",
        },
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "style": "max-width: 12em",
            },
        ),
    )

    coefficient = forms.CharField(
        label="Coefficient",
        help_text="Enter a decimal number",
        validators=[],
        required=False,
        error_messages={
            "invalid": "Coefficient is invalid",
        },
        widget=forms.TextInput(attrs={"style": "max-width: 6em"}),
    )

    main_order_number = forms.ModelChoiceField(
        label="Main order number",
        help_text="Select a main order number",
        queryset=PreferentialQuotaOrderNumber.objects.all(),
        validators=[],
        error_messages={
            "invalid": "Main Order number is invalid",
        },
        required=False,
        to_field_name="main_order_number_id",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, reference_document_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "main_order_number"
        ].choices = reference_document_version.preferential_quota_order_numbers.all().values_list(
            "id",
            "quota_order_number",
        )
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.text(
                "quota_order_number",
            ),
            "coefficient",
            "main_order_number",
            "start_date",
            "end_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class PreferentialQuotaOrderNumberDeleteForm(forms.ModelForm):
    class Meta:
        model = PreferentialQuotaOrderNumber
        fields = []

    def __init__(self, *args, **kwargs):
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
