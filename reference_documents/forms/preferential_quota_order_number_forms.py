from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import ValidityPeriodForm
from reference_documents.models import PreferentialQuota
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

    def __init__(self, reference_document_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "main_order_number"
        ].queryset = reference_document_version.preferential_quota_order_numbers.all()
        self.reference_document_version = reference_document_version
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

    def clean_coefficient(self):
        cleaned_data = super().clean()
        coefficient = cleaned_data.get("coefficient")
        if coefficient == "":
            return None

        return coefficient

    def clean(self):
        cleaned_data = super().clean()
        coefficient = cleaned_data.get("coefficient")
        main_order_number = cleaned_data.get("main_order_number")

        # cant have one without the other
        if coefficient and not main_order_number:
            raise ValidationError(
                "Coefficient specified without main order number",
            )
        elif not coefficient and main_order_number:
            raise ValidationError(
                "Main order number specified without coefficient",
            )

    def clean_quota_order_number(self):
        data = self.cleaned_data["quota_order_number"]
        if self.instance._state.adding:
            if self.reference_document_version.preferential_quota_order_numbers.filter(
                quota_order_number=data,
            ).exists():
                raise ValidationError("Quota Order Number Already Exists")

        return data

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

    main_order_number_id = forms.ModelChoiceField(
        label="Main order number",
        help_text="Select a main order number",
        queryset=PreferentialQuotaOrderNumber.objects.all(),
        validators=[],
        error_messages={
            "invalid": "Main Order number is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PreferentialQuotaOrderNumberDeleteForm(forms.Form):
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

    def clean(self):
        cleaned_data = super().clean()
        quota_order_number = self.instance
        versions = PreferentialQuota.objects.all().filter(
            preferential_quota_order_number=quota_order_number,
        )
        if versions:
            raise forms.ValidationError(
                f"Quota Order Number {quota_order_number} cannot be deleted as it has"
                f" associated Preferential Quotas.",
            )

        return cleaned_data

    class Meta:
        model = PreferentialQuotaOrderNumber
        fields = []
