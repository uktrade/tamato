from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from additional_codes import models
from common.forms import CreateDescriptionForm
from common.forms import DescriptionForm
from common.forms import ValidityPeriodForm


class AdditionalCodeForm(ValidityPeriodForm):
    code = forms.CharField(
        label="Additional code ID",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "type"
        ].label_from_instance = lambda obj: f"{obj.sid} - {obj.description}"
        self.fields["type"].label = "Additional code type"
        self.fields["type"].required = False

        if self.instance:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "You can't edit this"
            self.fields[
                "code"
            ].initial = f"{self.instance.type.sid}{self.instance.code}"

            self.fields["type"].disabled = True
            self.fields["type"].help_text = "You can't edit this"

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Field.text(
                "code",
                field_width=Fixed.TEN,
            ),
            Field("type"),
            Field("start_date"),
            Field("end_date"),
            Submit("submit", "Save"),
        )

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.sid:
            cleaned_data["sid"] = self.instance.sid

        # get type from instance if not submitted
        ctype = cleaned_data.get("type")
        if not ctype and self.instance and self.instance.type:
            ctype = self.instance.type

        return cleaned_data

    class Meta:
        model = models.AdditionalCode
        fields = ("type", "valid_between")


class AdditionalCodeDescriptionForm(DescriptionForm):
    class Meta:
        model = models.AdditionalCodeDescription
        fields = DescriptionForm.Meta.fields


class AdditionalCodeCreateDescriptionForm(CreateDescriptionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(
            0,
            Field(
                "described_additionalcode",
                type="hidden",
            ),
        )
        self.fields["description"].label = "Additional code description"

    class Meta:
        model = models.AdditionalCodeDescription
        fields = ("described_additionalcode", "description", "validity_start")
