from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.forms import CreateDescriptionForm
from common.forms import DescriptionForm
from common.forms import ValidityPeriodForm
from footnotes import models


class FootnoteForm(ValidityPeriodForm):
    code = forms.CharField(
        label="Footnote ID",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "footnote_type"
        ].label_from_instance = (
            lambda obj: f"{obj.footnote_type_id} - {obj.description}"
        )
        self.fields["footnote_type"].label = "Footnote type"
        self.fields["footnote_type"].required = False

        if self.instance:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "You can't edit this"
            self.fields["code"].initial = str(self.instance)

            self.fields["footnote_type"].disabled = True
            self.fields["footnote_type"].help_text = "You can't edit this"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            Field.text(
                "code",
                field_width=Fixed.TEN,
            ),
            Field("footnote_type"),
            Field("start_date"),
            Field("end_date"),
            Submit("submit", "Save"),
        )

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.footnote_id:
            cleaned_data["footnote_id"] = self.instance.footnote_id

        # get type from instance if not submitted
        footnote_type = cleaned_data.get("footnote_type")

        if not footnote_type and self.instance and self.instance.footnote_type:
            footnote_type = self.instance.footnote_type

        if not footnote_type:
            self.add_error("footnote_type", "Footnote type is required")

        return cleaned_data

    class Meta:
        model = models.Footnote
        fields = ("footnote_type", "valid_between")


class FootnoteDescriptionForm(DescriptionForm):
    class Meta:
        model = models.FootnoteDescription
        fields = DescriptionForm.Meta.fields


class FootnoteCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper.layout.insert(
            0,
            Field(
                "described_footnote",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Footnote description"

    class Meta:
        model = models.FootnoteDescription
        fields = ("described_footnote", "description", "validity_start")
