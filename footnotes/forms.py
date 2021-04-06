from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fixed
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms

from common.forms import DateInputFieldFixed
from common.forms import DescriptionForm
from common.forms import GovukDateRangeField
from common.util import TaricDateRange
from footnotes import models


class FootnoteForm(forms.ModelForm):
    code = forms.CharField(
        label="Footnote ID",
        required=False,
    )
    start_date = DateInputFieldFixed(
        label="Start date",
    )
    end_date = DateInputFieldFixed(
        help_text="Leave empty if a footnote is needed for an unlimited time",
        label="End date",
        required=False,
    )
    valid_between = GovukDateRangeField(required=False)

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
            Field("footnote_type", context={"label_size": "govuk-label--s"}),
            Field("start_date", context={"legend_size": "govuk-label--s"}),
            Field("end_date", context={"legend_size": "govuk-label--s"}),
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
            raise ValidationError({"footnote_type": "Footnote type is required"})

        # combine start and end dates into date range
        start_date = cleaned_data.pop("start_date", None)
        end_date = cleaned_data.pop("end_date", None)
        cleaned_data["valid_between"] = TaricDateRange(start_date, end_date)

        return cleaned_data

    class Meta:
        model = models.Footnote
        fields = ("footnote_type", "valid_between")


class FootnoteDescriptionForm(DescriptionForm):
    class Meta:
        model = models.FootnoteDescription
        fields = ("description", "valid_between")
