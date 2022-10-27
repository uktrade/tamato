from datetime import datetime

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from importer.forms import ImportForm


class CommodityFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Field.text("item_id", label_size=Size.SMALL),
            Field.text("active_state", label_size=Size.SMALL),
            Button("submit", "Search and Filter", css_class="govuk-!-margin-top-6"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
            ),
        )


class CommodityImportForm(ImportForm):
    taric_file = forms.FileField(
        required=True,
        help_text="",
        label="Select an XML file",
    )
    xsd_file = settings.PATH_XSD_COMMODITIES_TARIC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "taric_file",
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    @transaction.atomic
    def save(self, user: User, workbasket_id: str, commit=True):
        # we don't ask the user to provide a name in the form so generate one here based on filename and timestamp
        now = datetime.now()
        current_time = now.strftime("%H%M%S")
        batch_name = f"{self.cleaned_data['taric_file'].name}_{current_time}"
        self.instance.name = batch_name
        batch = super().save(commit)

        self.process_file(
            self.cleaned_data["taric_file"],
            batch,
            user,
            workbasket_id=workbasket_id,
        )

        return batch

    class Meta(ImportForm.Meta):
        exclude = ImportForm.Meta.fields
