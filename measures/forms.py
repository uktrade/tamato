from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.forms import AutocompleteWidget
from common.forms import ValidityPeriodForm
from measures import models
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation


class AutoCompleteField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.widget = AutocompleteWidget(
            attrs={"label": kwargs["label"], "help_text": kwargs.get("help_text")},
        )
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        return self.to_python(value)


class MeasureForm(ValidityPeriodForm):
    measure_type = AutoCompleteField(
        label="Measure type",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=models.MeasureType.objects.latest_approved(),
    )
    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=Regulation.objects.latest_approved(),
    )
    goods_nomenclature = AutoCompleteField(
        label="Code and description",
        help_text="Select the 10 digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.latest_approved(),
        required=False,
    )
    additional_code = AutoCompleteField(
        label="Code and description",
        help_text="If applicable, select the additional code to which the measure applies.",
        queryset=AdditionalCode.objects.latest_approved(),
        required=False,
    )
    order_number = AutoCompleteField(
        label="Order number",
        help_text="Enter the quota order number if a quota measure type has been selected. Leave this field blank if the measure is not a quota.",
        queryset=QuotaOrderNumber.objects.latest_approved(),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()

        cleaned_data["sid"] = self.instance.sid

        return cleaned_data

    class Meta:
        model = models.Measure
        fields = (
            "valid_between",
            "measure_type",
            "generating_regulation",
            "goods_nomenclature",
            "additional_code",
            "order_number",
        )


class MeasureFilterForm(forms.Form):
    """Generic Filtering form which adds submit and clear buttons, and adds GDS
    formatting to field types."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Field.text("sid", label_size=Size.SMALL, field_width=Fluid.TWO_THIRDS),
                Field.text(
                    "goods_nomenclature",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "additional_code",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "order_number",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "measure_type",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "regulation",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "geographical_area",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "footnote",
                    label_size=Size.SMALL,
                    field_width=Fluid.TWO_THIRDS,
                ),
                css_class="govuk-grid-row quarters",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Div(
                Div(
                    Field.radios(
                        "start_date_modifier",
                        legend_size=Size.SMALL,
                        inline=True,
                    ),
                    "start_date",
                    css_class="govuk-grid-column-one-half form-group-margin-bottom-2",
                ),
                Div(
                    Field.radios(
                        "end_date_modifier",
                        legend_size=Size.SMALL,
                        inline=True,
                    ),
                    "end_date",
                    css_class="govuk-grid-column-one-half form-group-margin-bottom-2",
                ),
                css_class="govuk-grid-row govuk-!-margin-top-6",
            ),
            HTML(
                '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
            ),
            Button("submit", "Search and Filter", css_class="govuk-!-margin-top-6"),
            HTML(
                f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
            ),
        )
