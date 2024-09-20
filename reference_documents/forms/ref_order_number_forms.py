from decimal import Decimal
from decimal import InvalidOperation

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import ValidityPeriodForm
from quotas import validators
from quotas.validators import quota_order_number_validator
from reference_documents.models import RefOrderNumber
from reference_documents.models import RefQuotaDefinition


class RefOrderNumberCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    class Meta:
        model = RefOrderNumber
        fields = [
            "order_number",
            "coefficient",
            "relation_type",
            "main_order_number",
            "valid_between",
        ]

    def __init__(self, reference_document_version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["main_order_number"].queryset = (
            reference_document_version.ref_order_numbers.all()
        )

        # Add a blank default
        self.fields["relation_type"].choices = validators.SubQuotaType.choices
        self.fields["relation_type"].choices.insert(0, ("", "----"))

        self.reference_document_version = reference_document_version
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.text(
                "order_number",
            ),
            "coefficient",
            "relation_type",
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
        coefficient = self.cleaned_data["coefficient"]

        if coefficient == "" or coefficient is None:
            return None

        try:
            coefficient = Decimal(coefficient)
            return coefficient
        except InvalidOperation:
            raise ValidationError(
                "Coefficient is not a valid number",
            )

    def clean_order_number(self):
        data = self.cleaned_data["order_number"]
        if self.instance._state.adding:
            if self.reference_document_version.ref_order_numbers.filter(
                order_number=data,
            ).exists():
                raise ValidationError("Order number already exists")

        if not data.isnumeric():
            raise ValidationError("Order number is not numeric")
        else:
            return data

    def clean(self):
        cleaned_data = super().clean()
        coefficient = cleaned_data.get("coefficient")
        relation_type = cleaned_data.get("relation_type")
        main_order_number = cleaned_data.get("main_order_number")

        if main_order_number:
            if not coefficient:
                raise ValidationError(
                    "Sub quotas must have a coefficient",
                )

            elif not relation_type:
                raise ValidationError(
                    "Sub quotas must have a relation type",
                )
        else:
            if coefficient:
                raise ValidationError(
                    "You can only specify coefficient if a main quota is selected",
                )

            elif relation_type:
                raise ValidationError(
                    "You can only specify relation type if a main quota is selected",
                )

    order_number = forms.CharField(
        label="Order number",
        help_text="Enter a six digit number",
        validators=[quota_order_number_validator],
        error_messages={
            "invalid": "Quota order number is invalid",
            "required": "Quota order number is required",
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
            "invalid": "Coefficient is not a valid number",
        },
        widget=forms.TextInput(attrs={"style": "max-width: 6em"}),
    )

    relation_type = forms.ChoiceField(
        label="Relation type",
        help_text="If this is a sub-quota, what relation type is it. Leave blank if not a sub quota",
        choices=[],
        validators=[],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    main_order_number_id = forms.ModelChoiceField(
        label="Main order number",
        help_text="Select a main order number",
        queryset=RefOrderNumber.objects.all(),
        validators=[],
        error_messages={
            "invalid": "Main order number is invalid",
        },
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class RefOrderNumberDeleteForm(forms.Form):
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

    def clean(self):
        cleaned_data = super().clean()
        quota_order_number = self.instance
        versions = RefQuotaDefinition.objects.all().filter(
            ref_order_number=quota_order_number,
        )
        if versions:
            raise forms.ValidationError(
                f"Quota order number {quota_order_number} cannot be deleted as it has"
                f" associated preferential quotas.",
            )

        return cleaned_data

    class Meta:
        model = RefOrderNumber
        fields = []
