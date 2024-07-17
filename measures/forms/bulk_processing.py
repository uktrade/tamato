from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.urls import reverse


class CancelBulkProcessorTaskForm(forms.Form):
    """Confirm canceling a bulk processor task."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cancel_url = reverse("measure-create-process-queue")

        self.helper = FormHelper(self)
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Div(
                Submit(
                    "submit",
                    "Terminate measure creation",
                    data_module="govuk-button",
                    data_prevent_double_click="true",
                    css_class="govuk-button govuk-button--warning",
                ),
                HTML(
                    f'<a href="{cancel_url}" role="button" draggable="false" '
                    f'class="govuk-button govuk-button--secondary" '
                    f'data-module="govuk-button">Cancel</a>',
                ),
                css_class="govuk-button-group",
            ),
        )
