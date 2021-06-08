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
from geo_areas.models import GeographicalArea
from measures import models
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket


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
    geographical_area = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.latest_approved(),
        required=False,
    )
    geographical_area_group = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.latest_approved().filter(
            area_code=1,
        ),
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
        empty_label=None,
    )
    geographical_area_country_or_region = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.latest_approved().exclude(
            area_code=1,
        ),
        widget=forms.Select(attrs={"class": "govuk-select"}),
        required=False,
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        self.fields[
            "order_number"
        ].queryset = QuotaOrderNumber.objects.approved_up_to_transaction(tx)
        self.fields[
            "measure_type"
        ].queryset = models.MeasureType.objects.approved_up_to_transaction(tx)
        self.fields[
            "generating_regulation"
        ].queryset = Regulation.objects.approved_up_to_transaction(tx)
        self.fields[
            "goods_nomenclature"
        ].queryset = GoodsNomenclature.objects.approved_up_to_transaction(tx)
        self.fields[
            "order_number"
        ].queryset = QuotaOrderNumber.objects.approved_up_to_transaction(tx)
        self.fields[
            "additional_code"
        ].queryset = AdditionalCode.objects.approved_up_to_transaction(tx)
        self.fields[
            "geographical_area"
        ].queryset = GeographicalArea.objects.approved_up_to_transaction(tx)
        self.fields[
            "geographical_area_group"
        ].queryset = GeographicalArea.objects.approved_up_to_transaction(tx).filter(
            area_code=1,
        )
        self.fields[
            "geographical_area_country_or_region"
        ].queryset = GeographicalArea.objects.approved_up_to_transaction(tx).exclude(
            area_code=1,
        )

        self.initial_geographical_area = self.instance.geographical_area

        for field in ["geographical_area_group", "geographical_area_country_or_region"]:
            self.fields[
                field
            ].label_from_instance = lambda obj: obj.structure_description

        if self.instance.geographical_area.is_group():
            self.fields[
                "geographical_area_group"
            ].initial = self.instance.geographical_area

        if self.instance.geographical_area.is_single_region_or_country():
            self.fields[
                "geographical_area_country_or_region"
            ].initial = self.instance.geographical_area

    def clean(self):
        cleaned_data = super().clean()

        erga_omnes_instance = (
            GeographicalArea.objects.latest_approved()
            .as_at(self.instance.valid_between.lower)
            .get(
                area_code=1,
                area_id=1011,
            )
        )

        geographical_area_fields = {
            "all": erga_omnes_instance,
            "group": cleaned_data.get("geographical_area_group"),
            "single": cleaned_data.get("geographical_area_country_or_region"),
        }

        if self.data.get("geographical_area_choice"):
            cleaned_data["geographical_area"] = geographical_area_fields[
                self.data.get("geographical_area_choice")
            ]

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
            "geographical_area",
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
