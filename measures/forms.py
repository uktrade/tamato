from collections import defaultdict

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Button
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Fluid
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import ValidityPeriodForm
from common.util import validity_range_contains_range
from footnotes.models import Footnote
from geo_areas.forms import GeographicalAreaFormMixin
from geo_areas.forms import GeographicalAreaSelect
from geo_areas.models import GeographicalArea
from measures import models
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket


class MeasureForm(ValidityPeriodForm):
    measure_type = AutoCompleteField(
        label="Measure type",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=models.MeasureType.objects.all(),
    )
    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=Regulation.objects.all(),
    )
    goods_nomenclature = AutoCompleteField(
        label="Code and description",
        help_text="Select the 10 digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.all(),
        required=False,
    )
    additional_code = AutoCompleteField(
        label="Code and description",
        help_text="If applicable, select the additional code to which the measure applies.",
        queryset=AdditionalCode.objects.all(),
        required=False,
    )
    order_number = AutoCompleteField(
        label="Order number",
        help_text="Enter the quota order number if a quota measure type has been selected. Leave this field blank if the measure is not a quota.",
        queryset=QuotaOrderNumber.objects.all(),
        required=False,
    )
    geographical_area = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.all(),
        required=False,
    )
    geographical_area_group = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.filter(
            area_code=1,
        ),
        required=False,
        widget=forms.Select(attrs={"class": "govuk-select"}),
        empty_label=None,
    )
    geographical_area_country_or_region = forms.ModelChoiceField(
        queryset=GeographicalArea.objects.exclude(
            area_code=1,
        ),
        widget=forms.Select(attrs={"class": "govuk-select"}),
        required=False,
        empty_label=None,
    )
    footnotes = forms.ModelMultipleChoiceField(
        queryset=Footnote.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        WorkBasket.get_current_transaction(self.request)

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
            "footnotes",
        )


class MeasureFilterForm(forms.Form):
    """Generic Filtering form which adds submit and clear buttons, and adds GDS
    formatting to field types."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Div(
                Field.text("sid", field_width=Fluid.TWO_THIRDS),
                Field.text(
                    "goods_nomenclature",
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "additional_code",
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "order_number",
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "measure_type",
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "regulation",
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "geographical_area",
                    field_width=Fluid.TWO_THIRDS,
                ),
                Field.text(
                    "footnote",
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


class MeasureCreateStartForm(forms.Form):
    pass


class MeasureDetailsForm(
    GeographicalAreaFormMixin,
    ValidityPeriodForm,
    forms.Form,
):
    class Meta:
        model = models.Measure
        fields = [
            "measure_type",
            "generating_regulation",
            "geographical_area",
            "order_number",
            "valid_between",
        ]

    measure_type = AutoCompleteField(
        label="Measure type",
        help_text="Select the appropriate measure type.",
        queryset=models.MeasureType.objects.all(),
    )
    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text="Select the regulation which provides the legal basis for the measure.",
        queryset=Regulation.objects.all(),
    )
    order_number = AutoCompleteField(
        label="Quota order number",
        help_text=(
            "Select the quota order number if a quota measure type has been selected. "
            "Leave this field blank if the measure is not a quota."
        ),
        queryset=QuotaOrderNumber.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["geographical_area"].required = False

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "measure_type",
            "generating_regulation",
            GeographicalAreaSelect("geographical_area"),
            "order_number",
            "start_date",
            "end_date",
            Submit("submit", "Continue"),
        )

    def clean(self):
        cleaned_data = super().clean()

        cleaned_data[self.prefix + "geographical_area"] = cleaned_data.pop(
            self.prefix + "geo_area",
            None,
        )

        if "measure_type" in cleaned_data and "valid_between" in cleaned_data:
            measure_type = cleaned_data["measure_type"]
            if not validity_range_contains_range(
                measure_type.valid_between,
                cleaned_data["valid_between"],
            ):
                raise ValidationError(
                    f"The date range of the measure can't be outside that of the measure type: {measure_type.valid_between} does not contain {cleaned_data['valid_between']}",
                )

        return cleaned_data


class MeasureCommodityForm(forms.Form):
    class Meta:
        model = models.Measure
        fields = [
            "goods_nomenclature",
            "additional_code",
        ]

    goods_nomenclature = AutoCompleteField(
        label="Commodity code",
        help_text="Select the 10-digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.all(),
    )
    additional_code = AutoCompleteField(
        label="Additional code",
        help_text="If applicable, select the additional code to which the measure applies.",
        queryset=AdditionalCode.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.layout = Layout(
            "goods_nomenclature",
            "additional_code",
            Submit("submit", "Continue"),
        )


class AddAnother(forms.BaseFormSet):
    """
    Adds the ability to add another form to the formset on submit.

    If the form POST data contains an "ADD" field with the value "1", the formset
    will be redisplayed with a new empty form appended.

    Deleting a subform will also redisplay the formset, with the order of the forms
    preserved.
    """

    extra = 1
    can_order = False
    can_delete = True
    max_num = 1000
    min_num = 0
    absolute_max = 1000
    validate_min = False
    validate_max = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.data.copy()

        formset_initial = defaultdict(dict)
        delete_forms = []
        for field, value in self.data.items():

            # filter out non-field data
            if field.startswith(f"{self.prefix}-"):
                form, field_name = field.rsplit("-", 1)

                # remove from data, so we can rebuild later
                if form != self.prefix:
                    del data[field]

                # group by subform
                if value:
                    formset_initial[form].update({field_name: value})

                if field_name == "DELETE" and value == "1":
                    delete_forms.append(form)

        # ignore management form
        try:
            del formset_initial[self.prefix]
        except KeyError:
            pass

        # ignore deleted forms
        for form in delete_forms:
            del formset_initial[form]

            # leave DELETE field in data for is_valid
            data[f"{form}-DELETE"] = 1

        for i, (form, form_initial) in enumerate(formset_initial.items()):
            for field, value in form_initial.items():

                # convert submitted value to python object
                form_field = self.form.declared_fields.get(field)
                if form_field:
                    form_initial[field] = form_field.widget.value_from_datadict(
                        form_initial,
                        {},
                        field,
                    )

                # reinsert into data, with updated numbering
                data[f"{self.prefix}-{i}-{field}"] = value

        self.initial = list(formset_initial.values())
        num_initial = len(self.initial)

        if num_initial < 1:
            data[f"{self.prefix}-ADD"] = "1"

        # update management data
        data[f"{self.prefix}-INITIAL_FORMS"] = num_initial
        data[f"{self.prefix}-TOTAL_FORMS"] = num_initial
        self.data = data

    def is_valid(self):
        """Invalidates the formset if "Add another" or "Delete" are submitted,
        to redisplay the formset with an extra empty form or the selected form
        removed."""

        # reshow the form with an extra empty form if "Add another" was submitted
        if f"{self.prefix}-ADD" in self.data:
            return False

        # reshow the form with the deleted form(s) removed if "Delete" was submitted
        if any(field for field in self.data if field.endswith("-DELETE")):
            return False

        return super().is_valid()


class MeasureConditionsForm(forms.ModelForm):
    class Meta:
        model = models.MeasureCondition
        fields = [
            "condition_code",
            "duty_amount",
            "required_certificate",
            "action",
        ]

    condition_code = forms.ModelChoiceField(
        label="",
        queryset=models.MeasureConditionCode.objects.latest_approved(),
        empty_label="-- Please select a condition code --",
    )
    duty_amount = forms.DecimalField(
        label="Reference price (where applicable)",
        max_digits=10,
        decimal_places=3,
        required=False,
    )
    required_certificate = AutoCompleteField(
        label="Certificate, license or document",
        queryset=Certificate.objects.all(),
        required=False,
    )
    action = forms.ModelChoiceField(
        label="Action code",
        queryset=models.MeasureAction.objects.latest_approved(),
        empty_label="-- Please select an action code --",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                Field("condition_code"),
                Div(
                    Field("duty_amount", css_class="govuk-input"),
                    "required_certificate",
                    "action",
                    css_class="govuk-radios__conditional",
                ),
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
                legend="Condition code",
                legend_size=Size.SMALL,
            ),
        )


class MeasureConditionsFormSet(AddAnother):
    form = MeasureConditionsForm


class MeasureDutiesForm(forms.Form):
    duties = forms.CharField(
        label="Duties",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "duties",
                HTML.details(
                    "Help with duties",
                    "Enter the duty that applies to the measure. This is expressed as a percentage (e.g. 4%), a specific duty (e.g. 33 GBP/100kg) or a compound duty (e.g. 3.5% + 11 GBP/LTR).",
                ),
            ),
            Submit("submit", "Continue"),
        )


class MeasureFootnotesForm(forms.Form):
    footnote = AutoCompleteField(
        label="",
        queryset=Footnote.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "footnote",
            Field("DELETE", template="includes/common/formset-delete-button.jinja")
            if not self.prefix.endswith("__prefix__")
            else None,
        )


class MeasureFootnotesFormSet(AddAnother):
    form = MeasureFootnotesForm


class MeasureReviewForm(forms.Form):
    pass
