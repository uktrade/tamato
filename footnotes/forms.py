from django import forms
from psycopg2.extras import DateTimeTZRange

from common.forms import GovukDateField
from common.forms import GovukDateRangeField
from footnotes import models


class FootnoteForm(forms.ModelForm):
    valid_between = GovukDateRangeField()

    class Meta:
        model = models.Footnote
        fields = ("footnote_type", "footnote_id", "valid_between")


class FootnoteDescriptionForm(forms.ModelForm):
    valid_between = GovukDateRangeField()

    class Meta:
        model = models.FootnoteDescription
        fields = ("description", "valid_between")
