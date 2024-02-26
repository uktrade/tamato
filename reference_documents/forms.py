from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from reference_documents import models


class ReferenceDocumentForm(forms.ModelForm):
    title = forms.CharField(
        label="Reference Document title",
    )
    area_id = forms.CharField(
        label="Area ID",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"].label = "Reference Document title"
        self.fields["area_id"].help_text = "Two character ID for the area referenced"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text("title"),
            Field("area_id"),
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
