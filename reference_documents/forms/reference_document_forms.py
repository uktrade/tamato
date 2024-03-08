from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from geo_areas.validators import area_id_validator
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion


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
        model = ReferenceDocument
        fields = ["title", "area_id"]


class ReferenceDocumentDeleteForm(forms.Form):
    def __init__(self, *args, **kwargs) -> None:
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        reference_document = self.instance
        versions = ReferenceDocumentVersion.objects.all().filter(
            reference_document=reference_document,
        )
        if versions:
            raise forms.ValidationError(
                f"Reference Document {reference_document.area_id} cannot be deleted as it has"
                f" active versions.",
            )

        return cleaned_data
