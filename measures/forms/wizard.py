import datetime
from itertools import groupby
from typing import Dict

from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import HTML
from crispy_forms_gds.layout import Div
from crispy_forms_gds.layout import Field
from crispy_forms_gds.layout import Fieldset
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.timezone import make_aware

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import BindNestedFormMixin
from common.forms import DateInputFieldFixed
from common.forms import FormSet
from common.forms import RadioNested
from common.forms import RadioNestedWidget
from common.forms import SerializableFormMixin
from common.forms import ValidityPeriodForm
from common.forms import formset_factory
from common.forms import unprefix_formset_data
from common.serializers import deserialize_date
from common.serializers import serialize_date
from common.util import validity_range_contains_range
from common.validators import SymbolValidator
from geo_areas import constants
from geo_areas.forms import CountryRegionFormSet
from geo_areas.forms import ErgaOmnesExclusionsFormSet
from geo_areas.forms import GeoGroupExclusionsFormSet
from geo_areas.forms import GeoGroupForm
from geo_areas.models import GeographicalArea
from measures import models
from measures.constants import MEASURE_COMMODITIES_FORMSET_PREFIX
from measures.constants import MeasureEditSteps
from measures.duty_sentence_parser import DutySentenceParser as LarkDutySentenceParser
from measures.validators import validate_components_applicability
from measures.validators import validate_duties
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from regulations.models import Regulation
from workbaskets.forms import SelectableObjectsForm

from . import MeasureConditionsBaseFormSet
from . import MeasureConditionsFormMixin
from . import MeasureFootnotesForm
from . import MeasureGeoAreaInitialDataMixin


class MeasureConditionsWizardStepForm(MeasureConditionsFormMixin):
    # override methods that use form kwargs
    def __init__(self, *args, **kwargs):
        self.measure_start_date = kwargs.pop("measure_start_date", None)
        self.measure_type = kwargs.pop("measure_type", None)
        super().__init__(*args, **kwargs)

    def clean_applicable_duty(self):
        """
        Gets applicable_duty from cleaned data.

        We expect `measure_start_date` to be passed in. Uses
        `DutySentenceParser` to check that applicable_duty is a valid duty
        string.
        """
        applicable_duty = self.cleaned_data["applicable_duty"]

        if (
            applicable_duty
            and self.measure_type
            and self.measure_type.components_not_permitted
        ):
            raise ValidationError(
                f"Duties cannot be added to a condition for measure type {self.measure_type}",
            )

        if applicable_duty and self.measure_start_date is not None:
            duty_sentence_parser = LarkDutySentenceParser(date=self.measure_start_date)
            try:
                duty_sentence_parser.transform(applicable_duty)
            except (SyntaxError, ValidationError) as e:
                self.add_error("applicable_duty", e)
        return applicable_duty

    def clean(self):
        """
        We get the reference_price from cleaned_data and the measure_start_date
        from form kwargs.

        If reference_price is provided, we use DutySentenceParser with
        measure_start_date to check that we are dealing with a simple duty (i.e.
        only one component). We then update cleaned_data with key-value pairs
        created from this single, unsaved component.
        """
        cleaned_data = super().clean()

        return self.conditions_clean(cleaned_data, self.measure_start_date)


class MeasureConditionsWizardStepFormSet(
    SerializableFormMixin,
    MeasureConditionsBaseFormSet,
):
    form = MeasureConditionsWizardStepForm

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        measure_start_date = kwargs.get("form_kwargs", {}).get("measure_start_date")
        measure_type = kwargs.get("form_kwargs", {}).get("measure_type")

        serializable_kwargs = {
            "form_kwargs": {
                "measure_start_date": serialize_date(measure_start_date),
                "measure_type_pk": measure_type.pk if measure_type else None,
            },
        }

        return serializable_kwargs

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        measure_start_date = form_kwargs.get("form_kwargs", {}).get(
            "measure_start_date",
        )
        measure_type_pk = form_kwargs.get("form_kwargs", {}).get("measure_type_pk")
        measure_type = (
            models.MeasureType.objects.get(pk=measure_type_pk)
            if measure_type_pk
            else None
        )

        kwargs = {
            "form_kwargs": {
                "measure_start_date": deserialize_date(measure_start_date),
                "measure_type": measure_type,
            },
        }

        return kwargs


class MeasureCreateStartForm(forms.Form):
    pass


class MeasureDetailsForm(
    SerializableFormMixin,
    ValidityPeriodForm,
    forms.Form,
):
    MAX_COMMODITY_COUNT = 99

    class Meta:
        model = models.Measure
        fields = [
            "measure_type",
            "valid_between",
        ]

    measure_type = AutoCompleteField(
        label="Measure type",
        help_text=(
            "Search for a measure type using its ID number or a keyword. "
            "A dropdown list will appear after a few seconds. "
            "You can then select the measure type from the dropdown list."
        ),
        queryset=models.MeasureType.objects.all(),
    )

    min_commodity_count = forms.IntegerField(
        label="Commodity code count",
        help_text=(
            "Enter how many commodity codes you intend to apply to the measure. You can add more later, up to 99 in total."
        ),
        min_value=1,
        max_value=MAX_COMMODITY_COUNT,
        required=True,
        error_messages={
            "required": "Enter a number between 1 and 99",
            "min_value": "Enter a number between 1 and 99",
            "max_value": "Enter a number between 1 and 99",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "measure_type",
            "start_date",
            "end_date",
            Field("min_commodity_count", css_class="govuk-input govuk-input--width-2"),
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

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


class MeasureRegulationIdForm(
    SerializableFormMixin,
    forms.Form,
):
    class Meta:
        model = models.Measure
        fields = [
            "generating_regulation",
        ]

    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text=(
            "Search for a regulation using its ID number or a keyword. "
            "A dropdown list will appear after a few seconds. "
            "You can then select the regulation from the dropdown list."
        ),
        queryset=Regulation.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "generating_regulation",
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class MeasureQuotaOrderNumberForm(
    SerializableFormMixin,
    forms.Form,
):
    class Meta:
        model = models.Measure
        fields = [
            "order_number",
        ]

    order_number = AutoCompleteField(
        label="Quota order number",
        help_text=(
            "Search for a quota using its order number. "
            "You can then select the correct quota from the dropdown list. "
            "Selecting a quota will automatically populate the appropriate geographical areas on the next page."
        ),
        queryset=QuotaOrderNumber.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "order_number",
            HTML.details(
                "I don't know what my quota ID number is",
                f'You can search for the quota number by using <a href="{reverse("quota-ui-list")}" class="govuk-link">find and edit quotas</a>',
            ),
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class MeasureQuotaOriginsForm(
    SerializableFormMixin,
    SelectableObjectsForm,
):
    def clean(self):
        cleaned_data = super().clean()

        selected_origins = {key: value for key, value in cleaned_data.items() if value}
        if not selected_origins:
            raise ValidationError("Select one or more quota origins")

        origin_pks = [self.object_id_from_field_name(key) for key in selected_origins]
        origins = QuotaOrderNumberOrigin.objects.filter(pk__in=origin_pks).current()

        cleaned_data["geo_areas_and_exclusions"] = [
            {
                "geo_area": origin.geographical_area,
                "exclusions": list(origin.excluded_areas.current()),
            }
            for origin in origins
        ]
        return cleaned_data

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        return {
            "quota_order_number_origin_pks": [o.pk for o in kwargs["objects"]],
        }

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        return {
            "objects": QuotaOrderNumberOrigin.objects.filter(
                pk__in=form_kwargs.get("quota_order_number_origin_pks", []),
            ),
        }


class MeasureGeographicalAreaForm(
    SerializableFormMixin,
    MeasureGeoAreaInitialDataMixin,
    BindNestedFormMixin,
    forms.Form,
):
    """
    Used in the MeasureCreateWizard.

    Allows creation of multiple measures for multiple commodity codes and
    countries.
    """

    geo_area = RadioNested(
        label="",
        help_text=(
            "Choose the geographical area to which the measure applies. "
            "This can be a specific country or a group of countries, and exclusions can be specified. "
            "The measure will only apply to imports from or exports to the selected area."
        ),
        choices=constants.GeoAreaType.choices,
        nested_forms={
            constants.GeoAreaType.ERGA_OMNES.value: [ErgaOmnesExclusionsFormSet],
            constants.GeoAreaType.GROUP.value: [
                GeoGroupForm,
                GeoGroupExclusionsFormSet,
            ],
            constants.GeoAreaType.COUNTRY.value: [CountryRegionFormSet],
        },
        error_messages={"required": "A Geographical area must be selected"},
        widget=RadioNestedWidget(attrs={"id": "geo-area-form-field"}),
    )

    @property
    def erga_omnes_instance(self):
        return GeographicalArea.objects.current().erga_omnes().get()

    @property
    def geo_area_field_name(self):
        return f"{self.prefix}-geo_area"

    def get_countries_initial(self):
        initial = {}

        geo_area_type = self.initial.get(self.geo_area_field_name) or self.data.get(
            self.geo_area_field_name,
        )

        if geo_area_type == constants.GeoAreaType.COUNTRY.value:
            field_name = constants.FIELD_NAME_MAPPING[geo_area_type]
            prefix = constants.FORMSET_PREFIX_MAPPING[geo_area_type]
            initial_countries = []
            # if we just submitted the form, add the new data to initial
            if self.formset_submitted or self.whole_form_submit:
                new_data = unprefix_formset_data(prefix, self.data.copy())
                for g in new_data:
                    if g[field_name]:
                        id = int(g[field_name])
                        g[field_name] = GeographicalArea.objects.get(id=id)
                initial_countries = new_data

            initial[constants.FORMSET_PREFIX_MAPPING[geo_area_type]] = initial_countries

        return initial

    def get_initial_data(self):
        geographical_area_fields = {
            constants.GeoAreaType.ERGA_OMNES: self.erga_omnes_instance,
            constants.GeoAreaType.GROUP: self.data.get(
                f"{self.prefix}-geographical_area_group",
            ),
            constants.GeoAreaType.COUNTRY: self.data.get(
                f"{self.prefix}-geographical_area_country_or_region",
            ),
        }

        self.fields["geo_area"].initial = self.data.get(f"{self.prefix}-geo_area")

        nested_forms_initial = {}

        if self.fields["geo_area"].initial:
            nested_forms_initial["geographical_area"] = geographical_area_fields[
                self.fields["geo_area"].initial
            ]

        geo_area_initial_data = self.get_geo_area_initial()
        countries_initial_data = self.get_countries_initial()
        nested_forms_initial.update(geo_area_initial_data)
        nested_forms_initial.update(countries_initial_data)

        return nested_forms_initial

    def init_layout(self):
        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "geo_area",
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nested_forms_initial = self.get_initial_data()
        kwargs.pop("initial", None)
        self.bind_nested_forms(*args, initial=nested_forms_initial, **kwargs)
        self.init_layout()

    def clean(self):
        cleaned_data = super().clean()

        geo_area_choice = self.cleaned_data.get("geo_area")

        geographical_area_fields = {
            constants.GeoAreaType.GROUP: "geographical_area_group",
            constants.GeoAreaType.COUNTRY: "geographical_area_country_or_region",
        }

        if geo_area_choice:
            if not self.formset_submitted:
                if geo_area_choice == constants.GeoAreaType.ERGA_OMNES:
                    cleaned_data["geo_areas_and_exclusions"] = [
                        {"geo_area": self.erga_omnes_instance},
                    ]

                elif geo_area_choice == constants.GeoAreaType.GROUP:
                    data_key = constants.SUBFORM_PREFIX_MAPPING[geo_area_choice]
                    cleaned_data["geo_areas_and_exclusions"] = [
                        {"geo_area": cleaned_data[data_key]},
                    ]

                elif geo_area_choice == constants.GeoAreaType.COUNTRY:
                    field_name = geographical_area_fields[geo_area_choice]
                    data_key = constants.SUBFORM_PREFIX_MAPPING[geo_area_choice]
                    cleaned_data["geo_areas_and_exclusions"] = [
                        {"geo_area": geo_area[field_name]}
                        for geo_area in cleaned_data[data_key]
                    ]

                # format exclusions for all options
                geo_area_exclusions = cleaned_data.get(
                    constants.EXCLUSIONS_FORMSET_PREFIX_MAPPING[geo_area_choice],
                )
                if geo_area_exclusions:
                    exclusions = [
                        exclusion[constants.FIELD_NAME_MAPPING[geo_area_choice]]
                        for exclusion in geo_area_exclusions
                    ]
                    cleaned_data["geo_areas_and_exclusions"][0][
                        "exclusions"
                    ] = exclusions

        return cleaned_data

    def serializable_data(self, remove_key_prefix: str = "") -> Dict:
        # Perculiarly, serializable data in this form keeps its prefix.
        return super().serializable_data()

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        # Perculiarly, this Form requires a prefix of "geographical_area".
        return {
            "prefix": "geographical_area",
        }


class MeasureCommodityAndDutiesForm(forms.Form):
    commodity = AutoCompleteField(
        label="Commodity code",
        queryset=GoodsNomenclature.objects.all(),
        attrs={"min_length": 3},
        error_messages={"required": "Select a commodity code"},
    )

    duties = forms.CharField(
        label="Duties",
        required=False,
        validators=[SymbolValidator],
    )

    def __init__(self, *args, **kwargs):
        # remove measure_start_date from kwargs here because superclass will not be expecting it
        self.measure_start_date = kwargs.pop("measure_start_date", None)
        self.measure_type = kwargs.pop("measure_type", None)
        super().__init__(*args, **kwargs)

        delete_button = (
            Field("DELETE", template="includes/common/formset-delete-button.jinja")
            if not self.prefix.endswith("__prefix__")
            else None
        )

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.label_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                Div(
                    Div(
                        Field("commodity"),
                        css_class="govuk-grid-column-one-third",
                    ),
                    Div(
                        Field(
                            "duties",
                            css_class="duties",
                        ),
                        css_class="govuk-grid-column-two-thirds",
                    ),
                    css_class="govuk-grid-row",
                ),
                delete_button,
                css_class="tap-inline",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        # Associate duties with their form so that the
        # formset may later add form errors for invalid duties
        cleaned_data["form_prefix"] = int(self.prefix.rsplit("-", 1)[1])
        duties = cleaned_data.get("duties", "")
        if duties and self.measure_type and self.measure_type.components_not_permitted:
            raise ValidationError(
                {
                    "duties": f"Duties cannot be added to a commodity for measure type {self.measure_type}",
                },
            )

        commodity = cleaned_data.get("commodity", "")
        measure_explosion_level = (
            self.measure_type.measure_explosion_level if self.measure_type else None
        )
        if measure_explosion_level and not commodity.item_id.endswith(
            "0" * (10 - measure_explosion_level),
        ):
            self.add_error(
                "commodity",
                f"Commodity must sit at {measure_explosion_level} digit level or higher for measure type {self.measure_type}",
            )

        return cleaned_data


MeasureCommodityAndDutiesBaseFormSet = formset_factory(
    MeasureCommodityAndDutiesForm,
    prefix=MEASURE_COMMODITIES_FORMSET_PREFIX,
    formset=FormSet,
    min_num=1,
    max_num=99,
    extra=0,
    validate_min=True,
    validate_max=True,
)


class MeasureCommodityAndDutiesFormSet(
    SerializableFormMixin,
    MeasureCommodityAndDutiesBaseFormSet,
):
    def __init__(self, *args, **kwargs):
        min_commodity_count = kwargs.pop("min_commodity_count", 2)
        self.measure_start_date = kwargs.pop("measure_start_date", None)
        default_extra = 2
        self.extra = min_commodity_count - default_extra
        super().__init__(*args, **kwargs)

    def non_form_errors(self):
        self._non_form_errors = super().non_form_errors()
        for e in self._non_form_errors.as_data():
            if e.code == "too_few_forms":
                e.message = "Select one or more commodity codes"

        return self._non_form_errors

    def clean(self):
        if any(self.errors):
            return

        cleaned_data = super().cleaned_data
        data = tuple((data["duties"], data["form_prefix"]) for data in cleaned_data)
        # Filter tuples(duty, form) for unique duties to avoid parsing the same duty more than once
        duties = [next(group) for duty, group in groupby(data, key=lambda x: x[0])]
        duty_sentence_parser = LarkDutySentenceParser(
            date=self.measure_start_date or make_aware(datetime.datetime.now()),
        )
        for duty, form in duties:
            try:
                duty_sentence_parser.transform(duty)
            except (SyntaxError, ValidationError) as e:
                self.forms[form].add_error(
                    "duties",
                    e,
                )

        return cleaned_data

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        measure_type = kwargs.get("form_kwargs", {}).get("measure_type")
        measure_type_pk = measure_type.pk if measure_type else None

        serializable_kwargs = {
            "min_commodity_count": kwargs.get("min_commodity_count"),
            "measure_start_date": serialize_date(kwargs.get("measure_start_date")),
            "form_kwargs": {
                "measure_type_pk": measure_type_pk,
            },
        }

        return serializable_kwargs

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        measure_type_pk = form_kwargs.get("form_kwargs", {}).get("measure_type_pk")
        measure_type = (
            models.MeasureType.objects.get(pk=measure_type_pk)
            if measure_type_pk
            else None
        )

        kwargs = {
            "min_commodity_count": form_kwargs.get("min_commodity_count"),
            "measure_start_date": deserialize_date(
                form_kwargs.get("measure_start_date"),
            ),
            "form_kwargs": {
                "measure_type": measure_type,
            },
        }

        return kwargs


class MeasureAdditionalCodeForm(
    SerializableFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = models.Measure
        fields = [
            "additional_code",
        ]

    additional_code = AutoCompleteField(
        label="Additional code",
        help_text=(
            "Search for an additional code by typing in the code's number or a keyword. "
            "A dropdown list will appear after a few seconds. You can then select the correct code from the dropdown list."
        ),
        queryset=AdditionalCode.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "additional_code",
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class MeasureFootnotesFormSet(
    SerializableFormMixin,
    FormSet,
):
    form = MeasureFootnotesForm

    def clean(self):
        """
        Hook for formset-wide cleaning to check if the same footnote has been
        added more than once.

        If so, raises a ValidationError that will be accessibile via
        formset.non_form_errors()
        """
        cleaned_data = super().cleaned_data
        footnotes = [d["footnote"] for d in cleaned_data if "footnote" in d]
        num_unique = len(set(footnotes))
        if len(footnotes) != num_unique:
            raise ValidationError("The same footnote cannot be added more than once")
        return cleaned_data


class MeasureReviewForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.measure_type = kwargs.pop("measure_type", None)
        self.commodities_data = kwargs.pop("commodities_data", None)
        self.conditions_data = kwargs.pop("conditions_data", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        validate_components_applicability(
            measure_type=self.measure_type,
            commodities_data=self.commodities_data,
            conditions_data=self.conditions_data,
        )
        return super().clean()


# MeasureEditWizard
class MeasuresEditFieldsForm(forms.Form):
    fields_to_edit = forms.MultipleChoiceField(
        choices=MeasureEditSteps.choices,
        widget=forms.CheckboxSelectMultiple,
        label="",
        help_text="Select the fields you wish to edit",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "fields_to_edit",
            ),
            Submit(
                "submit",
                "Continue",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )


class MeasureStartDateForm(forms.Form, SerializableFormMixin):
    start_date = DateInputFieldFixed(
        label="Start date",
        help_text="For example, 27 3 2008",
    )

    def __init__(self, *args, **kwargs):
        self.selected_measures = kwargs.pop("selected_measures", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "start_date",
            Submit(
                "submit",
                "Save measure start dates",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        if "start_date" in cleaned_data:
            start_date = cleaned_data["start_date"]
            for measure in self.selected_measures:
                end_date = measure.valid_between.upper
                if end_date and start_date > end_date:
                    raise ValidationError(
                        f"The start date cannot be after the end date: "
                        f"Start date {start_date:%d/%m/%Y} does not start before {end_date:%d/%m/%Y}",
                    )

        return cleaned_data

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        selected_measures = kwargs.get("selected_measures")
        selected_measures_pks = []
        for measure in selected_measures:
            selected_measures_pks.append(measure.id)

        serializable_kwargs = {
            "selected_measures": selected_measures_pks,
        }

        return serializable_kwargs

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        serialized_selected_measures_pks = form_kwargs.get("selected_measures")
        deserialized_selected_measures = models.Measure.objects.filter(
            pk__in=serialized_selected_measures_pks,
        )

        kwargs = {
            "selected_measures": deserialized_selected_measures,
        }

        return kwargs


class MeasureEndDateForm(forms.Form, SerializableFormMixin):
    end_date = DateInputFieldFixed(
        label="End date",
        help_text="For example, 27 3 2008",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.selected_measures = kwargs.pop("selected_measures", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            "end_date",
            Submit(
                "submit",
                "Save measure end dates",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        end_date = cleaned_data.get("end_date", None)
        if end_date:
            for measure in self.selected_measures:
                start_date = measure.valid_between.lower
                if start_date > end_date:
                    raise ValidationError(
                        f"The end date cannot be before the start date: "
                        f"Start date {start_date:%d/%m/%Y} does not start before {end_date:%d/%m/%Y}",
                    )
        else:
            cleaned_data["end_date"] = None

        return cleaned_data

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        selected_measures = kwargs.get("selected_measures")
        selected_measures_pks = []
        for measure in selected_measures:
            selected_measures_pks.append(measure.id)

        serializable_kwargs = {
            "selected_measures": selected_measures_pks,
        }

        return serializable_kwargs

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        serialized_selected_measures_pks = form_kwargs.get("selected_measures")
        deserialized_selected_measures = models.Measure.objects.filter(
            pk__in=serialized_selected_measures_pks,
        )

        kwargs = {
            "selected_measures": deserialized_selected_measures,
        }

        return kwargs


class MeasureRegulationForm(forms.Form, SerializableFormMixin):
    generating_regulation = AutoCompleteField(
        label="Regulation ID",
        help_text="Select the regulation which provides the legal basis for the measures.",
        queryset=Regulation.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        self.selected_measures = kwargs.pop("selected_measures", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "generating_regulation",
            ),
            Submit(
                "submit",
                "Save measure regulations",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        selected_measures = kwargs.get("selected_measures")
        selected_measures_pks = []
        for measure in selected_measures:
            selected_measures_pks.append(measure.id)

        serializable_kwargs = {
            "selected_measures": selected_measures_pks,
        }

        return serializable_kwargs

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        serialized_selected_measures_pks = form_kwargs.get("selected_measures")
        deserialized_selected_measures = models.Measure.objects.filter(
            pk__in=serialized_selected_measures_pks,
        )

        kwargs = {
            "selected_measures": deserialized_selected_measures,
        }

        return kwargs


class MeasureDutiesForm(forms.Form, SerializableFormMixin):
    duties = forms.CharField(
        label="Duties",
        help_text="Enter the duty that applies to the measures.",
    )

    def __init__(self, *args, **kwargs):
        self.selected_measures = kwargs.pop("selected_measures", None)
        self.measures_start_date = kwargs.pop("measures_start_date", None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "duties",
                HTML.details(
                    "Help with duties",
                    "This is expressed as a percentage (for example, 4%), "
                    "a specific duty (for example, 33 GBP/100kg) "
                    "or a compound duty (for example, 3.5% + 11 GBP / 100 kg).",
                ),
            ),
            Submit(
                "submit",
                "Save measure duties",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        duties = cleaned_data.get("duties", "")
        if self.measures_start_date:
            validate_duties(duties, self.measures_start_date)
        else:
            for measure in self.selected_measures:
                validate_duties(duties, measure.valid_between.lower)

        return cleaned_data

    @classmethod
    def serializable_init_kwargs(cls, kwargs: Dict) -> Dict:
        selected_measures = kwargs.get("selected_measures")
        selected_measures_pks = []
        for measure in selected_measures:
            selected_measures_pks.append(measure.id)

        serializable_kwargs = {
            "selected_measures": selected_measures_pks,
        }

        return serializable_kwargs

    @classmethod
    def deserialize_init_kwargs(cls, form_kwargs: Dict) -> Dict:
        serialized_selected_measures_pks = form_kwargs.get("selected_measures")
        deserialized_selected_measures = models.Measure.objects.filter(
            pk__in=serialized_selected_measures_pks,
        )

        kwargs = {
            "selected_measures": deserialized_selected_measures,
        }

        return kwargs


class MeasureGeographicalAreaExclusionsForm(forms.Form):
    excluded_area = forms.ModelChoiceField(
        label="",
        queryset=GeographicalArea.objects.all(),
        help_text="Select a geographical area to be excluded",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["excluded_area"].queryset = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )

        self.fields["excluded_area"].label_from_instance = (
            lambda obj: f"{obj.area_id} - {obj.description}"
        )

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.legend_size = Size.SMALL
        self.helper.layout = Layout(
            Fieldset(
                "excluded_area",
            ),
        )


class MeasureGeographicalAreaExclusionsFormSet(FormSet, SerializableFormMixin):
    """Allows editing the geographical area exclusions of multiple measures in
    `MeasureEditWizard`."""

    form = MeasureGeographicalAreaExclusionsForm
