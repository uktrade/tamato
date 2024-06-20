from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.forms import DateInputFieldFixed
from reference_documents.models import ReferenceDocumentVersion, RefRate, RefOrderNumber


class ReferenceDocumentVersionsCreateUpdateForm(forms.ModelForm):
    version = forms.CharField(
        label="Version number",
        error_messages={
            "required": "A version number is required",
            "invalid": "Version must be a number",
            "unique": "This version number already exists",
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
        model = ReferenceDocumentVersion
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
        preferential_duty_rates = RefRate.objects.all().filter(
            reference_document_version=reference_document_version,
        )
        tariff_quotas = RefOrderNumber.objects.all().filter(
            reference_document_version=reference_document_version,
        )
        if preferential_duty_rates or tariff_quotas:
            raise forms.ValidationError(
                f"Reference document version {reference_document_version.version} cannot be deleted as it has"
                f" current preferential duty rates or tariff quotas",
            )

        return cleaned_data
