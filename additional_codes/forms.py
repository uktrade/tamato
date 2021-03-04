from crispy_forms_gds.fields import DateInputField
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms

from additional_codes import models


class AdditionalCodeDescriptionForm(forms.ModelForm):
    start_date = DateInputField(
        label="Description start date",
    )

    description = forms.CharField(
        label="Additional code description",
        widget=forms.Textarea,
        help_text="Edit or overwrite the existing description",
    )

    def __init__(self, *args, **kwargs):
        super(AdditionalCodeDescriptionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("start_date", context={"legend_size": "govuk-label--s"}),
            Field.textarea("description", label_size=Size.SMALL, rows=5),
            Button("submit", "Finish"),
        )

    class Meta:
        model = models.AdditionalCodeDescription
        fields = ["description"]
