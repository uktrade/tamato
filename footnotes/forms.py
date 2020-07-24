from django import forms
from psycopg2.extras import DateTimeTZRange

from common.forms import GovukDateField
from common.forms import GovukDateRangeField
from footnotes import models


class FootnoteForm(forms.ModelForm):
    start_date = GovukDateField()
    end_date = GovukDateField(required=False)

    class Meta:
        model = models.Footnote
        fields = ("footnote_type", "footnote_id", "start_date", "end_date")

    def __init__(self, initial=None, *args, **kwargs):
        super().__init__(initial=initial, *args, **kwargs)
        if self.instance:
            self.initial["start_date"] = self.instance.valid_between.lower
            self.initial["end_date"] = self.instance.valid_between.upper

    def clean(self):
        self.cleaned_data["valid_between"] = DateTimeTZRange(
            lower=self.cleaned_data.get("start_date", None),
            upper=self.cleaned_data.get("end_date", None),
        )
        return self.cleaned_data


class FootnoteDescriptionForm(forms.ModelForm):
    valid_between = GovukDateRangeField(required=True)

    class Meta:
        model = models.FootnoteDescription
        fields = ("description", "valid_between")
