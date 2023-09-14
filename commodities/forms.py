from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.forms import widgets

from commodities.models.orm import FootnoteAssociationGoodsNomenclature
from commodities.models.orm import GoodsNomenclature
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from footnotes.models import Footnote


class CommodityFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            Accordion(
                AccordionSection(
                    "Search and filter",
                    Div(
                        Div(
                            Field.text(
                                "item_id",
                                field_width=Fluid.FULL,
                            ),
                            css_class="govuk-grid-column-one-half",
                        ),
                        Div(
                            Field.text(
                                "descriptions__description",
                                field_width=Fluid.FULL,
                            ),
                            css_class="govuk-grid-column-one-half",
                        ),
                        css_class="govuk-grid-row",
                    ),
                    Div(
                        Div(
                            Field.text("active_state", field_width=Fluid.ONE_THIRD),
                            css_class="govuk-grid-column-one-third",
                        ),
                        Div(
                            Field.text("with_footnotes", field_width=Fluid.ONE_THIRD),
                            legend="Footnotes",
                            css_class="govuk-grid-column-one-third",
                        ),
                        Div(
                            Field.text(
                                "current_work_basket",
                                field_width=Fluid.ONE_THIRD,
                            ),
                            css_class="govuk-grid-column-one-third",
                        ),
                        css_class="govuk-grid-row",
                    ),
                    Button(
                        "submit",
                        "Search and Filter",
                    ),
                    HTML(
                        f'<a class="govuk-button govuk-button--secondary" href="{self.clear_url}"> Clear </a>',
                    ),
                    css_class="govuk-accordion__section--expanded",
                ),
            ),
        )


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

    associated_footnote = forms.ModelChoiceField(
        label="Footnote",
        help_text=(
            "Search for a footnote by typing in the footnote's number or a keyword. "
            "A dropdown list will appear after a few seconds. You can then select the correct footnote from the dropdown list."
        ),
        queryset=Footnote.objects.all(),
        error_messages={"required": "Select a footnote for this commodity code"},
        widget=widgets.Select(
            attrs={
                "class": "autocomplete-progressive-enhancement",
                "id": "associated-footnote-select",
            },
        ),
    )

    def init_fields(self):
        self.fields[
            "end_date"
        ].help_text = "Leave empty if the footnote is needed for an unlimited time"
        self.fields[
            "associated_footnote"
        ].queryset = Footnote.objects.approved_up_to_transaction(self.tx).filter(
            footnote_type__application_code__in=[1, 2],
        )
        self.fields[
            "associated_footnote"
        ].label_from_instance = (
            lambda obj: f"{obj.structure_code} - {obj.structure_description}"
        )

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
        self.tx = kwargs.pop("tx")
        super().__init__(*args, **kwargs)
        self.init_fields()
        self.init_layout()


class CommodityFootnoteEditForm(CommodityFootnoteForm):
    pass


FootnoteAssociationGoodsNomenclatureDeleteForm = delete_form_for(
    FootnoteAssociationGoodsNomenclature,
)
