from django import forms
from django.urls import reverse

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field, Layout, Size, Submit, Button, HTML
from crispy_forms_gds.templatetags.crispy_forms_gds import button_link


class SearchFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            HTML(
                f'<a class="govuk-button govuk-button--secondary" href="{reverse("additional_code-ui-list")}"> Clear </a>'
            ),
        )
