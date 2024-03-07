from decimal import Decimal

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from common.forms import DateInputFieldFixed
from common.forms import ValidityPeriodForm
from geo_areas.validators import area_id_validator
from reference_documents import models
from reference_documents.models import PreferentialQuota
from reference_documents.models import PreferentialRate
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.validators import commodity_code_validator
from reference_documents.validators import order_number_validator


class PreferentialRateCreateUpdateForm(
    ValidityPeriodForm,
    forms.ModelForm,
):
    commodity_code = forms.CharField(
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
            "required": "This is required",
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
        model = PreferentialRate
        fields = [
            "commodity_code",
            "duty_rate",
            "valid_between",
        ]


class ReferenceDocumentCreateUpdateForm(forms.ModelForm):
    title = forms.CharField(
        label="Reference Document title",
        error_messages={
            "required": "A Reference Document title is required",
            "unique": "A Reference Document with this title already exists",
        },
    )
    area_id = forms.CharField(
        label="Area ID",
        validators=[area_id_validator],
        error_messages={
            "required": "An area ID is required",
            "unique": "A Reference Document with this area ID already exists",
            "invalid": "Enter the area ID in the correct format",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "title"
        ].help_text = "For example, 'Reference document for XX' where XX is the Area ID"
        self.fields["area_id"].help_text = "Two character ID for the area referenced"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text(
                "title",
                field_width=Fixed.TWENTY,
            ),
            Field.text(
                "area_id",
                field_width=Fixed.TEN,
            ),
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    class Meta:
        model = models.ReferenceDocument
        fields = ["title", "area_id"]


class ReferenceDocumentDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        reference_document = self.instance
        versions = models.ReferenceDocumentVersion.objects.all().filter(
            reference_document=reference_document,
        )
        if versions:
            raise forms.ValidationError(
                f"Reference Document {reference_document.area_id} cannot be deleted as it has"
                f" active versions.",
            )

        return cleaned_data


class PreferentialRateDeleteForm(forms.ModelForm):
    class Meta:
        model = PreferentialRate
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


class ReferenceDocumentVersionsEditCreateForm(forms.ModelForm):
    version = forms.CharField(
        label="Version number",
        error_messages={
            "required": "A version number is required",
            "invalid": "Version must be a number",
        },
    )
    published_date = DateInputFieldFixed(
        label="Published date",
    )
    entry_into_force_date = DateInputFieldFixed(
        label="Entry into force date",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["published_date"].error_messages[
            "required"
        ] = "A published date is required"
        self.fields["entry_into_force_date"].error_messages[
            "required"
        ] = "An entry into force date is required"
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field(
                "reference_document",
                type="hidden",
            ),
            Field.text(
                "version",
                field_width=Fixed.TEN,
            ),
            "published_date",
            "entry_into_force_date",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        ref_doc = cleaned_data.get("reference_document")
        if cleaned_data.get("version"):
            try:
                latest_version = ReferenceDocumentVersion.objects.filter(
                    reference_document=ref_doc,
                ).latest("created_at")
                if float(cleaned_data.get("version")) < latest_version.version:
                    raise forms.ValidationError(
                        "New versions of this reference document must be a higher number than previous versions",
                    )
            except ReferenceDocumentVersion.DoesNotExist:
                pass

    class Meta:
        model = models.ReferenceDocumentVersion
        fields = [
            "reference_document",
            "version",
            "published_date",
            "entry_into_force_date",
        ]


class ReferenceDocumentVersionDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        reference_document_version = self.instance
        preferential_duty_rates = models.PreferentialRate.objects.all().filter(
            reference_document_version=reference_document_version,
        )
        tariff_quotas = models.PreferentialQuotaOrderNumber.objects.all().filter(
            reference_document_version=reference_document_version,
        )
        if preferential_duty_rates or tariff_quotas:
            raise forms.ValidationError(
                f"Reference Document version {reference_document_version.version} cannot be deleted as it has"
                f" current preferential duty rates or tariff quotas",
            )

        return cleaned_data
