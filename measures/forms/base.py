import logging

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Accordion
from crispy_forms_gds.layout import AccordionSection
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms

from common.fields import AutoCompleteField
from common.forms import FormSet
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from footnotes.models import Footnote
from measures import models

logger = logging.getLogger(__name__)


class MeasureValidityForm(ValidityPeriodForm):
    """A form for working with `start_date` and `end_date` logic where the
    `valid_between` field does not already exist on the form."""

    class Meta:
        model = models.Measure
        fields = [
            "valid_between",
        ]


class MeasureFilterForm(forms.Form):
    """Generic Filtering form which adds submit and clear buttons, and adds GDS
    formatting to field types."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Accordion(
                AccordionSection(
                    "Search and filter",
                    HTML(
                        '<h3 class="govuk-body">Select one or more options to search</h3>',
                    ),
                    Div(
                        Div(
                            Div(
                                "goods_nomenclature",
                                Field.text("sid", field_width=Fluid.TWO_THIRDS),
                                "regulation",
                                "footnote",
                                css_class="govuk-grid-column-one-third",
                            ),
                            Div(
                                "goods_nomenclature__item_id",
                                "additional_code",
                                "measure_type",
                                css_class="govuk-grid-column-one-third",
                            ),
                            Div(
                                "order_number",
                                "certificates",
                                "geographical_area",
                                css_class="govuk-grid-column-one-third",
                            ),
                            css_class="govuk-grid-row",
                        ),
                        HTML(
                            '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                        ),
                        HTML(
                            '<h3 class="govuk-body">Filters</h3>',
                        ),
                        Div(
                            Div(
                                Field.radios("measure_filters_modifier", inline=True),
                                css_class="govuk-grid-column-full form-group-margin-bottom-2",
                            ),
                            Div(
                                "modc",
                                HTML(
                                    "<h3 class='govuk-body'>To use the 'Include inherited measures' filter, enter a valid commodity code in the 'Specific commodity code' filter above</h3>",
                                ),
                                css_class="govuk-grid-column-full form-group-margin-bottom-2",
                            ),
                            css_class="govuk-grid-row govuk-!-margin-top-6",
                        ),
                        HTML(
                            '<hr class="govuk-section-break govuk-section-break--s govuk-section-break--visible">',
                        ),
                        HTML(
                            '<p class="govuk-body">Time period</p>',
                        ),
                        Div(
                            Div(
                                Field.radios(
                                    "start_date_modifier",
                                    inline=True,
                                ),
                                "start_date",
                                css_class="govuk-grid-column-one-half form-group-margin-bottom-2",
                            ),
                            Div(
                                Field.radios(
                                    "end_date_modifier",
                                    inline=True,
                                ),
                                "end_date",
                                css_class="govuk-grid-column-one-half form-group-margin-bottom-2",
                            ),
                            css_class="govuk-grid-row govuk-!-padding-top-6",
                        ),
                        Div(
                            Div(
                                Button(
                                    "submit",
                                    "Search and filter",
                                    css_class="govuk-!-margin-top-6",
                                ),
                                HTML(
                                    f'<a class="govuk-button govuk-button--secondary govuk-!-margin-top-6" href="{self.clear_url}"> Clear </a>',
                                ),
                                css_class="govuk-grid-column-full govuk-button-group govuk-!-padding-top-6",
                            ),
                            css_class="govuk-grid-row govuk-!-padding-top-3",
                        ),
                    ),
                    css_class="govuk-grid-row govuk-!-padding-3 black-label--no-button govuk-accordion__section--expanded",
                    id="accordion-open-close-section",
                ),
            ),
        )


class MeasureFootnotesForm(forms.Form):
    footnote = AutoCompleteField(
        label="",
        help_text=(
            "Search for a footnote by typing in the footnote's number or a keyword. "
            "A dropdown list will appear after a few seconds. You can then select the correct footnote from the dropdown list."
        ),
        queryset=Footnote.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "footnote",
                (
                    Field(
                        "DELETE",
                        template="includes/common/formset-delete-button.jinja",
                    )
                    if not self.prefix.endswith("__prefix__")
                    else None
                ),
                legend="Footnote",
                legend_size=Size.SMALL,
            ),
        )


class MeasureUpdateFootnotesForm(MeasureFootnotesForm):
    """
    Used with edit measure, this form has two buttons each submitting to
    different routes: one for submitting to the edit measure view
    (MeasureUpdate) and the other for submitting to the edit measure footnote
    view (MeasureFootnotesUpdate).

    This is done by setting the submit button's "formaction" attribute. This
    requires that the path is passed here on kwargs, allowing it to be accessed
    and used when rendering the edit forms' submit buttons.
    """

    def __init__(self, *args, **kwargs):
        path = kwargs.pop("path")
        if "edit" in path:
            self.path = path[:-1] + "-footnotes/"

        super().__init__(*args, **kwargs)


class MeasureUpdateFootnotesFormSet(FormSet):
    form = MeasureUpdateFootnotesForm


MeasureDeleteForm = delete_form_for(models.Measure)
