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

from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from commodities.models.orm import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import ValidityPeriodForm
from footnotes.models import Footnote
from importer.forms import ImportForm


class CommodityFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Field.text("item_id", label_size=Size.SMALL),
            Field.text("descriptions__description", label_size=Size.SMALL),
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


class CommodityFootnoteForm(ValidityPeriodForm, forms.ModelForm):
    class Meta:
        model = FootnoteAssociationGoodsNomenclature
        fields = [
            "goods_nomenclature",
            "associated_footnote",
            "valid_between",
        ]

    goods_nomenclature = forms.ModelChoiceField(
        queryset=GoodsNomenclature.objects.all(),
        widget=forms.HiddenInput(),
    )

    associated_footnote = AutoCompleteField(
        label="Footnote",
        help_text=(
            "Search for a footnote by typing in the footnote's number or a keyword. "
            "A dropdown list will appear after a few seconds. You can then select the correct footnote from the dropdown list."
        ),
        queryset=Footnote.objects.all(),
        error_messages={"required": "Select a footnote for this commodity code"},
    )

    def init_fields(self):
        self.fields[
            "end_date"
        ].help_text = "Leave empty if the footnote is needed for an unlimited time"

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "start_date",
            "end_date",
            "goods_nomenclature",
            "associated_footnote",
            Submit(
                "submit",
                "Save",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()
