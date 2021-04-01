from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from additional_codes import models
from common.forms import DateInputFieldFixed
from common.forms import DescriptionForm
from common.forms import GovukDateRangeField
from common.util import TaricDateRange


class AdditionalCodeForm(forms.ModelForm):
    code = forms.CharField(
        label="Additional code ID",
        required=False,
    )
    start_date = DateInputFieldFixed(
        label="Start date",
    )
    end_date = DateInputFieldFixed(
        help_text="Leave empty if an additional code is needed for an unlimited time",
        label="End date",
        required=False,
    )
    valid_between = GovukDateRangeField(required=False)

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

            if self.instance.valid_between.lower:
                self.fields["start_date"].initial = self.instance.valid_between.lower
            if self.instance.valid_between.upper:
                self.fields["end_date"].initial = self.instance.valid_between.upper

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field.text(
                "code",
                field_width=Fixed.TEN,
                label_size=Size.SMALL,
            ),
            Field("type", context={"label_size": "govuk-label--s"}),
            Field("start_date", context={"legend_size": "govuk-label--s"}),
            Field("end_date", context={"legend_size": "govuk-label--s"}),
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

        # combine start and end dates into date range
        start_date = cleaned_data.pop("start_date", None)
        end_date = cleaned_data.pop("end_date", None)
        cleaned_data["valid_between"] = TaricDateRange(start_date, end_date)

        return cleaned_data

    class Meta:
        model = models.AdditionalCode
        fields = ("type", "valid_between")


class AdditionalCodeDescriptionForm(DescriptionForm):
    class Meta:
        model = models.AdditionalCodeDescription
        fields = ("description", "valid_between")
