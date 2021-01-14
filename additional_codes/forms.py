from django import forms

from crispy_forms_gds.choices import Choice
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field, Layout, Size, Submit, Button


class SearchFilterForm(forms.Form):

    TYPES = (
        Choice('2', '2 - Tariff preference'),
        Choice('3', '3 - Prohibition / Restriction / Surveillance'),
        Choice('4', '4 - Restrictions'),
        Choice('6', '6 - Agricultural Tables (non-Meursing)'),
        Choice('8', '8 - Anti-dumping / countervailing'),
        Choice('9', '9 - Export Refunds'),
        Choice('A', 'A - Anti-dumping / countervailing'),
        Choice('B', 'B - Anti-dumping / countervailing'),
        Choice('C', 'C - Anti-dumping / countervailing'),
        Choice('D', 'D - Dual Use'),
        Choice('P', 'P - Refund for basic products'),
        Choice('T', 'T - This is the additional code type for UK trade remedies from 2021'),
        Choice('V', 'V - VAT'),
        Choice('X', 'X - EXCISE'),
    )

    START_YEAR = (
        Choice('2021', '2021'),
        Choice('2020', '2020'),
        Choice('2019', '2019'),
        Choice('2018', '2018'),
        Choice('2017', '2017'),
        Choice('2016', '2016'),
        Choice('2015', '2015'),
        Choice('2014', '2014'),
        Choice('2013', '2013'),
        Choice('2012', '2012'),
    )

    ACTIVE_STATE = (
        Choice('active', 'Active'),
        Choice('terminated', 'Terminated'),
    )

    search = forms.CharField(label='Search')

    additional_code_type = forms.MultipleChoiceField(
        choices=TYPES,
        widget=forms.CheckboxSelectMultiple,
        label="Additional code type",
        help_text="Select all that apply",
    )

    start_year = forms.MultipleChoiceField(
        choices=START_YEAR,
        widget=forms.CheckboxSelectMultiple,
        label="Start year",
        help_text="Select all that apply",
    )

    active_state = forms.MultipleChoiceField(
        choices=ACTIVE_STATE,
        widget=forms.CheckboxSelectMultiple,
        label="Active state",
        help_text="Select all that apply",
    )

    def __init__(self, *args, **kwargs):
        super(SearchFilterForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field.text("search", label_size=Size.SMALL),
            Field.checkboxes(
                "additional_code_type",
                legend_size=Size.SMALL,
            ),
            Field.checkboxes(
                "start_year",
                legend_size=Size.SMALL,
            ),
            Field.checkboxes(
                "active_state",
                legend_size=Size.SMALL,
            ),
            Button("submit", "Search and Filter"),
            Button.secondary("clear", "Clear")
        )
