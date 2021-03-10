from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms


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
