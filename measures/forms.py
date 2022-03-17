import logging
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
from django.template import loader

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import ValidityPeriodForm
from common.forms import delete_form_for
from common.util import validity_range_contains_range
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.forms import GeographicalAreaFormMixin
from geo_areas.forms import GeographicalAreaSelect
from geo_areas.models import GeographicalArea
from measures import models
from measures.validators import validate_duties
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


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
        attrs={"min_length": 3},
    )
    duty_sentence = forms.CharField(
        label="Duties",
        widget=forms.TextInput,
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        WorkBasket.get_current_transaction(self.request)

        if not hasattr(self.instance, "duty_sentence"):
            raise AttributeError(
                "Measure instance is missing `duty_sentence` attribute. Try calling `with_duty_sentence` queryset method",
            )

        self.initial["duty_sentence"] = self.instance.duty_sentence
        self.request.session[
            f"instance_duty_sentence_{self.instance.sid}"
        ] = self.instance.duty_sentence

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

        # If no footnote keys are stored in the session for a measure,
        # store all the pks of a measure's footnotes on the session, using the measure sid as key
        if f"instance_footnotes_{self.instance.sid}" not in self.request.session.keys():
            self.request.session[f"instance_footnotes_{self.instance.sid}"] = [
                footnote.pk for footnote in self.instance.footnotes.all()
            ]

    def clean_duty_sentence(self):
        duty_sentence = self.cleaned_data["duty_sentence"]
        valid_between = self.initial.get("valid_between")
        if duty_sentence and valid_between is not None:
            validate_duties(duty_sentence, valid_between.lower)

        return duty_sentence

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

    def save(self, commit=True):
        """Get the measure instance after form submission, get from session
        storage any footnote pks created via the Footnote formset and any pks
        not removed from the measure after editing and create footnotes via
        FootnoteAssociationMeasure."""
        instance = super().save(commit=False)
        if commit:
            instance.save()

        sid = instance.sid

        if (
            self.request.session[f"instance_duty_sentence_{self.instance.sid}"]
            != self.cleaned_data["duty_sentence"]
        ):
            self.instance.diff_components(
                self.cleaned_data["duty_sentence"],
                self.cleaned_data["valid_between"].lower,
                WorkBasket.current(self.request),
            )

        footnote_pks = [
            dct["footnote"]
            for dct in self.request.session.get(f"formset_initial_{sid}", [])
        ]
        footnote_pks.extend(self.request.session.get(f"instance_footnotes_{sid}", []))

        self.request.session.pop(f"formset_initial_{sid}", None)
        self.request.session.pop(f"instance_footnotes_{sid}", None)

        for pk in footnote_pks:
            footnote = (
                Footnote.objects.filter(pk=pk)
                .approved_up_to_transaction(instance.transaction)
                .first()
            )
            models.FootnoteAssociationMeasure.objects.create(
                footnoted_measure=instance,
                associated_footnote=footnote,
                update_type=UpdateType.CREATE,
                transaction=instance.transaction,
            )

        return instance

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
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Div(
                Field.text("sid", field_width=Fluid.TWO_THIRDS),
                "goods_nomenclature",
                "additional_code",
                "order_number",
                "measure_type",
                "regulation",
                "geographical_area",
                "footnote",
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
                    f"The date range of the measure can't be outside that of the measure type: "
                    f"{measure_type.valid_between} does not contain {cleaned_data['valid_between']}",
                )

        return cleaned_data


class MeasureAdditionalCodeForm(forms.ModelForm):
    class Meta:
        model = models.Measure
        fields = [
            "additional_code",
        ]

    additional_code = AutoCompleteField(
        label="Additional code",
        help_text="If applicable, select the additional code to which the measure applies.",
        queryset=AdditionalCode.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "additional_code",
            Submit("submit", "Continue"),
        )


class FormSet(forms.BaseFormSet):
    """
    Adds the ability to add another form to the formset on submit.

    If the form POST data contains an "ADD" field with the value "1", the formset
    will be redisplayed with a new empty form appended.

    Deleting a subform will also redisplay the formset, with the order of the forms
    preserved.
    """

    extra = 0
    can_order = False
    can_delete = True
    max_num = 1000
    min_num = 0
    absolute_max = 1000
    validate_min = False
    validate_max = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we have form data, then capture the any user "add form" or
        # "delete form" actions.
        self.formset_action = None
        if f"{self.prefix}-ADD" in self.data:
            self.formset_action = "ADD"
        else:
            for field in self.data:
                if field.endswith("-DELETE"):
                    self.formset_action = "DELETE"
                    break

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

        # Re-present the form to show the result of adding another form or
        # deleting an existing one.
        if self.formset_action == "ADD" or self.formset_action == "DELETE":
            return False

        # An empty set of forms is valid.
        if self.total_form_count() == 0:
            return True

        return super().is_valid()


class MeasureCommodityAndDutiesForm(forms.Form):
    commodity = AutoCompleteField(
        label="Commodity code",
        help_text="Select the 10-digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.all(),
        attrs={"min_length": 3},
    )

    duties = forms.CharField(
        label="Duties",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.label_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "commodity",
                "duties",
                HTML(
                    loader.render_to_string(
                        "components/duty_help.jinja",
                        context={"component": "measure"},
                    ),
                ),
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        duties = cleaned_data.get("duties", "")
        measure_start_date = self.initial.get("measure_start_date")
        if measure_start_date is not None and duties:
            validate_duties(duties, measure_start_date)

        return cleaned_data


class MeasureCommodityAndDutiesFormSet(FormSet):
    form = MeasureCommodityAndDutiesForm


class MeasureConditionComponentDuty(Field):
    template = "components/measure_condition_component_duty/template.jinja"


class MeasureConditionsForm(forms.ModelForm):
    class Meta:
        model = models.MeasureCondition
        fields = [
            "condition_code",
            "duty_amount",
            "required_certificate",
            "action",
            "applicable_duty",
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
    applicable_duty = forms.CharField(
        label="Duty",
        required=False,
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
                    MeasureConditionComponentDuty("applicable_duty"),
                    css_class="govuk-radios__conditional",
                ),
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
                legend="Condition code",
                legend_size=Size.SMALL,
            ),
        )


class MeasureConditionsFormSet(FormSet):
    form = MeasureConditionsForm


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
            Fieldset(
                "footnote",
                Field("DELETE", template="includes/common/formset-delete-button.jinja")
                if not self.prefix.endswith("__prefix__")
                else None,
                legend="Footnote",
                legend_size=Size.SMALL,
            ),
        )


class MeasureFootnotesFormSet(FormSet):
    form = MeasureFootnotesForm


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


class MeasureReviewForm(forms.Form):
    pass


MeasureDeleteForm = delete_form_for(models.Measure)
