import datetime

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from django import forms
from django.core.exceptions import ValidationError

from certificates.models import Certificate
from common.fields import AutoCompleteField
from common.forms import FormSet
from common.forms import FormSetSubmitMixin
from common.forms import unprefix_formset_data
from common.validators import SymbolValidator
from geo_areas import constants
from geo_areas.models import GeographicalArea
from measures import models
from measures.constants import MEASURE_CONDITIONS_FORMSET_PREFIX
from measures.duty_sentence_parser import DutySentenceParser as LarkDutySentenceParser
from measures.validators import validate_conditions_formset

from . import MeasureConditionComponentDuty


class MeasureConditionsBaseFormSet(FormSet):
    prefix = MEASURE_CONDITIONS_FORMSET_PREFIX

    def clean(self):
        """
        We get the cleaned_data from the forms in the formset if any of the
        forms are not valid the form set checks are skipped until they are
        valid.

        Validates formset using validate_conditions_formset which will raise a
        ValidationError if the formset contains errors.
        """
        # cleaned_data is only set if forms are all valid
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        cleaned_data = []
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            cleaned_data += [form.cleaned_data]

        actions = [form["action"] for form in cleaned_data]
        negative_actions = models.MeasureActionPair.objects.filter(
            negative_action__in=actions,
        ).values_list("negative_action", flat=True)
        validate_conditions_formset(cleaned_data, negative_actions)

        return cleaned_data


class MeasureGeoAreaInitialDataMixin(FormSetSubmitMixin):
    def get_geo_area_initial(self):
        initial = {}
        geo_area_type = self.initial.get(self.geo_area_field_name) or self.data.get(
            self.geo_area_field_name,
        )
        if geo_area_type in [
            constants.GeoAreaType.GROUP.value,
            constants.GeoAreaType.ERGA_OMNES.value,
        ]:
            field_name = constants.FIELD_NAME_MAPPING[geo_area_type]
            prefix = constants.FORMSET_PREFIX_MAPPING[geo_area_type]
            initial_exclusions = []
            if hasattr(self, "instance"):
                initial_exclusions = [
                    {field_name: exclusion.excluded_geographical_area}
                    for exclusion in self.instance.exclusions.all()
                ]
            # if we just submitted the form, add the new data to initial
            if self.formset_submitted or self.whole_form_submit:
                new_data = unprefix_formset_data(prefix, self.data.copy())
                for g in new_data:
                    if g[field_name]:
                        id = int(g[field_name])
                        g[field_name] = GeographicalArea.objects.get(id=id)
                initial_exclusions = new_data

            initial[constants.FORMSET_PREFIX_MAPPING[geo_area_type]] = (
                initial_exclusions
            )

        return initial


class MeasureConditionsFormMixin(forms.ModelForm):
    class Meta:
        model = models.MeasureCondition
        fields = [
            "condition_code",
            "duty_amount",
            "monetary_unit",
            "condition_measurement",
            "required_certificate",
            "action",
            "applicable_duty",
            "condition_sid",
        ]

    condition_code = forms.ModelChoiceField(
        label="",
        queryset=models.MeasureConditionCode.objects.latest_approved(),
        empty_label="-- Please select a condition code --",
        error_messages={"required": "A condition code is required."},
    )
    # This field used to be called duty_amount, but forms.ModelForm expects a decimal value when it sees that duty_amount is a DecimalField on the MeasureCondition model.
    # reference_price expects a non-compound duty string (e.g. "11 GBP / 100 kg".
    # Using DutySentenceParser we validate this string and get the decimal value to pass to the model field, duty_amount)
    reference_price = forms.CharField(
        label="Reference price or quantity",
        required=False,
        validators=[
            SymbolValidator,
        ],
    )
    required_certificate = AutoCompleteField(
        label="Certificate, licence or document",
        queryset=Certificate.objects.current(),
        required=False,
    )
    action = forms.ModelChoiceField(
        label="Action code",
        # Filters out 'negative' actions in a positive/negative pair, doesn't filter out action that have no pair
        queryset=models.MeasureAction.objects.latest_approved()
        .filter(
            negative_measure_action__isnull=True,
        )
        .select_related("negative_measure_action")
        .order_by("code"),
        empty_label="-- Please select an action code --",
        error_messages={"required": "An action code is required."},
    )
    applicable_duty = forms.CharField(
        label="Duty",
        required=False,
        validators=[
            SymbolValidator,
        ],
    )
    condition_sid = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Fieldset(
                Div(
                    Div(
                        Div(
                            Field(
                                "condition_code",
                                template="components/measure_condition_code/template.jinja",
                            ),
                            "condition_sid",
                        ),
                        Div(
                            Div(
                                Field("reference_price", css_class="govuk-input"),
                                "required_certificate",
                                css_class="govuk-form-group",
                            ),
                            css_class="govuk-radios__conditional",
                        ),
                    ),
                    Div(
                        Field(
                            "action",
                            template="components/measure_condition_action_code/template.jinja",
                        ),
                        Div(
                            MeasureConditionComponentDuty("applicable_duty"),
                        ),
                    ),
                    style="display: grid; grid-template-columns: 80% 80%; grid-gap: 5%",
                ),
                (
                    Field(
                        "DELETE",
                        template="includes/common/formset-delete-button.jinja",
                    )
                    if not self.prefix.endswith("__prefix__")
                    else None
                ),
                legend="Condition",
                legend_size=Size.SMALL,
                data_field="condition_code",
            ),
        )

    def conditions_clean(
        self,
        cleaned_data,
        measure_start_date,
        is_negative_action_code=False,
    ):
        """
        We get the reference_price from cleaned_data and the measure_start_date
        from the form's initial data.

        If reference_price is provided, we use LarkDutySentenceParser with
        measure_start_date, if present, or the current date, to check that we
        are dealing with a simple duty (i.e. only one component). We then update
        cleaned_data with key-value pairs created from this single, unsaved
        component.

        Args:
            cleaned_data: the cleaned data submitted in the form,
            measure_start_date: the start date set for the measure,
            is_negative_action_code: a boolean by default false and is used to
            carry out different validation depending on the action code type
        Returns:
            cleaned_data
        """
        price = cleaned_data.get("reference_price")
        certificate = cleaned_data.get("required_certificate")
        action = cleaned_data.get("action")

        # Note this is a quick fix & hard coded for now
        # Action code's 1,2,3,4 are flexible and have edge cases that all neither Price or certificate to be present
        if action:
            skip_price_and_reference_check = action.code in ["01", "02", "03", "04"]
        else:
            skip_price_and_reference_check = False
        # Price or certificate must be present but no both; if the action code is not negative
        if (
            not skip_price_and_reference_check
            and not is_negative_action_code
            and (price and certificate)
        ):
            self.add_error(
                None,
                ValidationError(
                    "For each condition you must complete either ‘reference price or quantity’ or ‘certificate, licence or document’.",
                ),
            )

        if price:
            date = measure_start_date or datetime.datetime.now()
            parser = LarkDutySentenceParser(compound_duties=False, date=date)
            try:
                components = parser.transform(price)
                cleaned_data["duty_amount"] = components[0].get("duty_amount")
                cleaned_data["monetary_unit"] = components[0].get("monetary_unit")
                cleaned_data["condition_measurement"] = (
                    models.Measurement.objects.as_at(date)
                    .filter(
                        measurement_unit=components[0].get("measurement_unit"),
                        measurement_unit_qualifier=components[0].get(
                            "measurement_unit_qualifier",
                        ),
                    )
                    .first()
                )
            except (SyntaxError, ValidationError) as error:
                self.add_error("reference_price", error)

        # The JS autocomplete does not allow for clearing unnecessary certificates
        # In case of a user changing data, the information is cleared here.
        condition_code = cleaned_data.get("condition_code")
        if condition_code and not condition_code.accepts_certificate:
            cleaned_data["required_certificate"] = None

        return cleaned_data
