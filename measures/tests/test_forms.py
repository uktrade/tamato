from unittest.mock import patch

import pytest
from django.forms.models import model_to_dict

from common.models.transactions import Transaction
from common.models.utils import set_current_transaction
from common.tests import factories
from geo_areas.validators import AreaCode
from measures import forms
from measures.forms import MeasureForm
from measures.models import Measure

pytestmark = pytest.mark.django_db

GEO_AREA_FORM_PREFIX = "geographical_area"
COUNTRY_REGION_FORM_PREFIX = "country_region"


@patch("measures.forms.diff_components")
def test_diff_components_not_called(
    diff_components,
    measure_form,
    duty_sentence_parser,
):
    measure_form.save(commit=False)

    assert diff_components.called == False


@patch("measures.forms.diff_components")
def test_diff_components_called(diff_components, measure_form, duty_sentence_parser):
    measure_form.data.update(duty_sentence="6.000%")
    measure_form.save(commit=False)

    assert diff_components.called == True


def test_measure_form_invalid_conditions_data(
    measure_form_data,
    session_with_workbasket,
    erga_omnes,
    duty_sentence_parser,
):
    """Tests that MeasureForm.is_valid() returns False when
    MeasureConditionsFormSet returns False."""
    prefix = "measure-conditions-formset"
    measure_form_data[f"{prefix}-TOTAL_FORMS"] = 1
    measure_form_data[f"{prefix}-INITIAL_FORMS"] = 0
    measure_form_data[f"{prefix}-MIN_NUM_FORMS"] = 0
    measure_form_data[f"{prefix}-MAX_NUM_FORMS"] = 1000
    measure_form_data[f"{prefix}-0-applicable_duty"] = "invalid"
    measure_form = MeasureForm(
        data=measure_form_data,
        initial={},
        instance=Measure.objects.first(),
        request=session_with_workbasket,
    )

    assert not measure_form.is_valid()


def test_measure_forms_details_valid_data(measure_type, regulation, erga_omnes):
    data = {
        "measure_type": measure_type.pk,
        "generating_regulation": regulation.pk,
        "order_number": None,
        "start_date_0": 2,
        "start_date_1": 4,
        "start_date_2": 2021,
        "geographical_area": erga_omnes.pk,
    }
    form = forms.MeasureDetailsForm(data, prefix="")
    assert form.is_valid()


def test_measure_forms_geo_area_valid_data_erga_omnes(erga_omnes):
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.ERGA_OMNES,
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert form.is_valid()


def test_measure_forms_geo_area_valid_data_erga_omnes_exclusions(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.ERGA_OMNES,
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": geo_area1.pk,
        "erga_omnes_exclusions_formset-1-erga_omnes_exclusion": geo_area2.pk,
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert form.is_valid()


def test_measure_forms_geo_area_valid_data_erga_omnes_exclusions_delete(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.ERGA_OMNES,
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": geo_area1.pk,
        "erga_omnes_exclusions_formset-0-DELETE": "1",
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_geo_group_exclusions(erga_omnes):
    geo_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.GROUP,
        f"{GEO_AREA_FORM_PREFIX}-geographical_area_group": geo_group.pk,
        "geo_group_exclusions_formset-0-geo_group_exclusion": geo_area1.pk,
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert form.is_valid()


def test_measure_forms_geo_area_valid_data_geo_group_exclusions_delete(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.GROUP,
        "geographical_area_group-geographical_area_group": geo_group.pk,
        "geo_group_exclusions_formset-0-geo_group_exclusion": geo_area1.pk,
        "geo_group_exclusions_formset-0-DELETE": "1",
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_erga_omnes_exclusions_add(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.ERGA_OMNES,
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": geo_area1.pk,
        "erga_omnes_exclusions_formset-ADD": "1",
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_geo_group(erga_omnes):
    geo_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.GROUP,
        f"{GEO_AREA_FORM_PREFIX}-geographical_area_group": geo_group.pk,
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert form.is_valid()
    # https://uktrade.atlassian.net/browse/TP2000-437 500 error where object instead of a list of objects
    assert type(form.cleaned_data["geo_area_list"]) == list


def test_measure_forms_geo_area_valid_data_countries(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.COUNTRY,
        "country_region_formset-0-geographical_area_country_or_region": geo_area1.pk,
        "country_region_formset-1-geographical_area_country_or_region": geo_area2.pk,
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert form.is_valid()


def test_measure_forms_geo_area_valid_data_countries_delete(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.COUNTRY,
        "country_region_formset-0-geographical_area_country_or_region": geo_area1.pk,
        "country_region_formset-1-geographical_area_country_or_region": geo_area2.pk,
        "country_region_formset-1-DELETE": "on",
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_countries_add(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.COUNTRY,
        "country_region_formset-0-geographical_area_country_or_region": geo_area1.pk,
        "country_region_formset-ADD": "1",
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()


def test_measure_forms_geo_area_invalid_data_geo_group(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.GROUP,
        "geographical_area_group-geographical_area_group": geo_area1.pk,
    }
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()
    assert "A country group is required." in form.errors["geo_area"][0]


@pytest.mark.parametrize(
    "data,error",
    [
        (
            {
                f"{GEO_AREA_FORM_PREFIX}-geo_area": forms.GeoAreaType.COUNTRY,
                "country_region_formset-0-geographical_area_country_or_region": "",
            },
            "Please submit 1 or more forms.",
        ),
        (
            {
                f"{GEO_AREA_FORM_PREFIX}-geo_area": "",
                "country_region_formset-0-geographical_area_country_or_region": "",
            },
            "A Geographical area must be selected",
        ),
    ],
)
def test_measure_forms_geo_area_invalid_data_error_messages(data, error, erga_omnes):
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureGeographicalAreaForm(
        data,
        initial={},
        prefix=GEO_AREA_FORM_PREFIX,
    )
    assert not form.is_valid()
    assert error in form.errors["geo_area"]


def test_measure_forms_details_invalid_data():
    data = {
        "measure_type": "foo",
        "generating_regulation": "bar",
        "order_number": None,
        "start_date_0": 2,
        "start_date_1": 4,
        "start_date_2": 2021,
    }
    form = forms.MeasureDetailsForm(data, initial={}, prefix="")
    error_string = [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    assert form.errors["measure_type"] == error_string
    assert form.errors["generating_regulation"] == error_string
    assert not form.is_valid()


def test_measure_forms_details_invalid_date_range(measure_type, regulation, erga_omnes):
    data = {
        "measure_type": measure_type.pk,
        "generating_regulation": regulation.pk,
        "order_number": None,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "geographical_area": erga_omnes.pk,
    }
    form = forms.MeasureDetailsForm(data, initial={}, prefix="")
    # In the real wizard view the prefix will be populated with the name of the form. It's left blank here to make the mock form data simpler
    assert not form.is_valid()
    assert (
        form.errors["__all__"][0]
        == "The date range of the measure can't be outside that of the measure type: [2020-01-01, None) does not contain [2000-01-01, None)"
    )


def test_measure_forms_additional_code_valid_data(additional_code):
    data = {
        "additional_code": additional_code.pk,
    }
    form = forms.MeasureAdditionalCodeForm(data, prefix="")
    assert form.is_valid()


def test_measure_forms_additional_code_invalid_data():
    data = {
        "additional_code": "foo",
    }
    form = forms.MeasureAdditionalCodeForm(data, prefix="")
    assert form.errors["additional_code"] == [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    assert not form.is_valid()


@pytest.mark.parametrize(
    "duties,is_valid",
    [("33 GBP/100kg", True), ("some invalid duty expression", False)],
)
def test_measure_forms_duties_form(duties, is_valid, duty_sentence_parser, date_ranges):
    commodity = factories.GoodsNomenclatureFactory.create()
    data = {
        "duties": duties,
        "commodity": commodity,
    }
    form = forms.MeasureCommodityAndDutiesForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )
    assert form.is_valid() == is_valid


def test_measure_forms_conditions_form_valid_data():
    """Tests that MeasureConditionsForm is valid when initialised with minimal
    required fields."""
    condition_code = factories.MeasureConditionCodeFactory.create()
    action = factories.MeasureActionFactory.create()
    data = {
        "condition_code": condition_code.pk,
        "action": action.pk,
    }
    # MeasureConditionsForm.__init__ expects prefix kwarg for instantiating crispy forms `Layout` object
    form = forms.MeasureConditionsForm(data, prefix="")

    assert form.is_valid()


def test_measure_forms_conditions_wizard_form_valid_data(date_ranges):
    """Tests that MeasureConditionsWizardStepForm is valid when initialised with
    minimal required fields."""
    condition_code = factories.MeasureConditionCodeFactory.create()
    action = factories.MeasureActionFactory.create()
    data = {
        "condition_code": condition_code.pk,
        "action": action.pk,
    }
    # MeasureConditionsForm.__init__ expects prefix kwarg for instantiating crispy forms `Layout` object
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )

    assert form.is_valid()


def test_measure_forms_conditions_form_invalid_data():
    """Tests that MeasureConditionsForm raises a validation error when a
    required field is missing."""
    action = factories.MeasureActionFactory.create()
    data = {
        "action": action.pk,
    }
    form = forms.MeasureConditionsForm(data, prefix="")

    assert not form.is_valid()
    assert form.errors["condition_code"][0] == "This field is required."


def test_measure_forms_conditions_wizard_form_invalid_data(date_ranges):
    """Tests that MeasureConditionsWizardStepForm raises a validation error when
    a required field is missing."""
    action = factories.MeasureActionFactory.create()
    data = {
        "action": action.pk,
    }
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )

    assert not form.is_valid()
    assert form.errors["condition_code"][0] == "This field is required."


def test_measure_forms_conditions_valid_duty(date_ranges, duty_sentence_parser):
    """Tests that, given a valid, non-compound duty (e.g. '11 GBP / 100 kg' as
    opposed to '11 GBP / 100 kg + 12 %') MeasureConditionsForm.clean() returns
    cleaned_data updated with values taken from unsaved measure component
    objects, as generated by the DutySentenceParser."""
    action = factories.MeasureActionFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    start_date = date_ranges.normal.lower
    data = {
        "condition_code": condition_code.pk,
        "reference_price": "11 GBP / 100 kg",
        "action": action.pk,
        "start_date_0": start_date.day,
        "start_date_1": start_date.month,
        "start_date_2": start_date.year,
    }
    form = forms.MeasureConditionsForm(data, prefix="")
    form.is_valid()

    assert form.cleaned_data["duty_amount"] == 11
    assert form.cleaned_data["monetary_unit"].code == "GBP"
    assert (
        form.cleaned_data["condition_measurement"].measurement_unit.abbreviation
        == "100 kg"
    )


def test_measure_forms_conditions_wizard_valid_duty(date_ranges, duty_sentence_parser):
    action = factories.MeasureActionFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    data = {
        "condition_code": condition_code.pk,
        "reference_price": "11 GBP / 100 kg",
        "action": action.pk,
    }
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )
    form.is_valid()

    assert form.cleaned_data["duty_amount"] == 11
    assert form.cleaned_data["monetary_unit"].code == "GBP"
    assert (
        form.cleaned_data["condition_measurement"].measurement_unit.abbreviation
        == "100 kg"
    )


@pytest.mark.parametrize(
    "reference_price, message",
    [
        ("invalid duty", "Enter a valid duty sentence."),
        (
            "3.5 % + 11 GBP / 100 kg",
            "A MeasureCondition cannot be created with a compound reference price (e.g. 3.5% + 11 GBP / 100 kg)",
        ),
    ],
)
def test_measure_forms_conditions_invalid_duty(
    reference_price,
    message,
    date_ranges,
    duty_sentence_parser,
):
    """Tests that, given an invalid or compound duty string,
    MeasureConditionsForm.clean raises a ValidationError with the appropriate
    error message."""
    action = factories.MeasureActionFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    start_date = date_ranges.normal.lower
    data = {
        "condition_code": condition_code.pk,
        "reference_price": reference_price,
        "action": action.pk,
        "start_date_0": start_date.day,
        "start_date_1": start_date.month,
        "start_date_2": start_date.year,
    }
    form = forms.MeasureConditionsForm(data, prefix="")

    assert not form.is_valid()
    assert message in form.errors["__all__"]


@pytest.mark.parametrize(
    "reference_price, message",
    [
        ("invalid duty", "Enter a valid duty sentence."),
        (
            "3.5 % + 11 GBP / 100 kg",
            "A MeasureCondition cannot be created with a compound reference price (e.g. 3.5% + 11 GBP / 100 kg)",
        ),
    ],
)
def test_measure_forms_conditions_wizard_invalid_duty(
    reference_price,
    message,
    date_ranges,
    duty_sentence_parser,
):
    """Tests that, given an invalid or compound duty string,
    MeasureConditionsWizardStepForm.clean raises a ValidationError with the
    appropriate error message."""
    action = factories.MeasureActionFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    data = {
        "condition_code": condition_code.pk,
        "reference_price": reference_price,
        "action": action.pk,
    }
    initial_data = {"measure_start_date": date_ranges.normal}
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
        initial=initial_data,
    )

    assert not form.is_valid()
    assert message in form.errors["__all__"]


@pytest.mark.parametrize(
    "applicable_duty, is_valid",
    [("33 GBP/100kg", True), ("3.5% + 11 GBP / 100 kg", True), ("invalid duty", False)],
)
def test_measure_forms_conditions_applicable_duty(
    applicable_duty,
    is_valid,
    date_ranges,
    duty_sentence_parser,
):
    """Tests that applicable_duty form field handles simple and complex duty
    sentence strings, raising an error, if an invalid string is passed."""
    action = factories.MeasureActionFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    start_date = date_ranges.normal.lower
    data = {
        "condition_code": condition_code.pk,
        "action": action.pk,
        "applicable_duty": applicable_duty,
        "start_date_0": start_date.day,
        "start_date_1": start_date.month,
        "start_date_2": start_date.year,
    }
    initial_data = {"measure_start_date": date_ranges.normal}
    form = forms.MeasureConditionsForm(data, prefix="", initial=initial_data)

    assert form.is_valid() == is_valid

    if not is_valid:
        assert "Enter a valid duty sentence." in form.errors["applicable_duty"]


@pytest.mark.parametrize(
    "applicable_duty, is_valid",
    [("33 GBP/100kg", True), ("3.5% + 11 GBP / 100 kg", True), ("invalid duty", False)],
)
def test_measure_forms_conditions_wizard_applicable_duty(
    applicable_duty,
    is_valid,
    date_ranges,
    duty_sentence_parser,
):
    """Tests that applicable_duty form field handles simple and complex duty
    sentence strings, raising an error, if an invalid string is passed."""
    action = factories.MeasureActionFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    data = {
        "condition_code": condition_code.pk,
        "action": action.pk,
        "applicable_duty": applicable_duty,
    }
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )

    assert form.is_valid() == is_valid

    if not is_valid:
        assert "Enter a valid duty sentence." in form.errors["applicable_duty"]


def test_measure_forms_conditions_clears_unneeded_certificate(date_ranges):
    """Tests that MeasureConditionsForm removes certificates that are not
    expected by the measure condition code."""
    certificate = factories.CertificateFactory.create()
    code_with_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=True,
    )
    code_without_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=False,
    )
    action = factories.MeasureActionFactory.create()
    initial_data = {"measure_start_date": date_ranges.normal}

    data = {
        "required_certificate": certificate.pk,
        "action": action.pk,
    }
    form_expects_certificate = forms.MeasureConditionsForm(
        dict(data, **{"condition_code": code_with_certificate.pk}),
        prefix="",
        initial=initial_data,
    )
    form_expects_certificate.is_valid()
    assert form_expects_certificate.cleaned_data["required_certificate"] == certificate

    form_expects_no_certificate = forms.MeasureConditionsForm(
        dict(data, **{"condition_code": code_without_certificate.pk}),
        prefix="",
        initial=initial_data,
    )
    assert form_expects_no_certificate.is_valid()
    assert form_expects_no_certificate.cleaned_data["required_certificate"] is None


def test_measure_forms_conditions_wizard_clears_unneeded_certificate(date_ranges):
    """Tests that MeasureConditionsWizardStepForm removes certificates that are
    not expected by the measure condition code."""
    certificate = factories.CertificateFactory.create()
    code_with_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=True,
    )
    code_without_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=False,
    )
    action = factories.MeasureActionFactory.create()

    data = {
        "required_certificate": certificate.pk,
        "action": action.pk,
    }
    form_expects_certificate = forms.MeasureConditionsWizardStepForm(
        dict(data, **{"condition_code": code_with_certificate.pk}),
        prefix="",
        measure_start_date=date_ranges.normal,
    )
    form_expects_certificate.is_valid()
    assert form_expects_certificate.cleaned_data["required_certificate"] == certificate

    form_expects_no_certificate = forms.MeasureConditionsWizardStepForm(
        dict(data, **{"condition_code": code_without_certificate.pk}),
        prefix="",
        measure_start_date=date_ranges.normal,
    )
    assert form_expects_no_certificate.is_valid()
    assert form_expects_no_certificate.cleaned_data["required_certificate"] is None


def test_measure_form_valid_data(erga_omnes, session_with_workbasket):
    measure = factories.MeasureFactory.create()
    data = model_to_dict(measure)
    data["geo_area"] = "COUNTRY"
    data["country_region-geographical_area_country_or_region"] = data[
        "geographical_area"
    ]
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureForm(
        data=data,
        initial={},
        instance=Measure.objects.first(),
        request=session_with_workbasket,
    )
    assert form.is_valid()


@pytest.mark.parametrize("initial_option", [("ERGA_OMNES"), ("GROUP"), ("COUNTRY")])
def test_measure_form_initial_data_geo_area(
    initial_option,
    erga_omnes,
    session_with_workbasket,
):
    group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    country = factories.GeographicalAreaFactory.create()
    choice_to_geo_area = {
        "ERGA_OMNES": erga_omnes,
        "GROUP": group,
        "COUNTRY": country,
    }
    geo_area_to_choice = {v: k for k, v in choice_to_geo_area.items()}
    measure = factories.MeasureFactory.create(
        geographical_area=choice_to_geo_area[initial_option],
    )
    data = model_to_dict(measure)
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )
    form = forms.MeasureForm(
        data=data,
        initial={},
        instance=Measure.objects.first(),
        request=session_with_workbasket,
    )
    assert form.initial["geo_area"] == geo_area_to_choice[measure.geographical_area]


def test_measure_form_cleaned_data_geo_exclusions_group(
    erga_omnes,
    session_with_workbasket,
):
    group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    excluded_country1 = factories.GeographicalAreaFactory.create()
    excluded_country2 = factories.GeographicalAreaFactory.create()
    measure = factories.MeasureFactory.create(geographical_area=group)
    data = model_to_dict(measure)
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )
    exclusions_data = {
        "geo_area": "GROUP",
        "geographical_area_group-geographical_area_group": group.pk,
        "geo_group_exclusions_formset-0-geo_group_exclusion": excluded_country1.pk,
        "geo_group_exclusions_formset-1-geo_group_exclusion": excluded_country2.pk,
    }
    data.update(exclusions_data)
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureForm(
        data=data,
        initial={},
        instance=Measure.objects.first(),
        request=session_with_workbasket,
    )
    assert form.is_valid()
    assert form.cleaned_data["exclusions"]
    assert not bool(
        set(form.cleaned_data["exclusions"]).difference(
            {excluded_country1, excluded_country2},
        ),
    )


def test_measure_form_cleaned_data_geo_exclusions_erga_omnes(
    erga_omnes,
    session_with_workbasket,
):
    excluded_country1 = factories.GeographicalAreaFactory.create()
    excluded_country2 = factories.GeographicalAreaFactory.create()
    factories.GeographicalAreaFactory.create()
    measure = factories.MeasureFactory.create(geographical_area=erga_omnes)
    data = model_to_dict(measure)
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )
    exclusions_data = {
        "geo_area": "ERGA_OMNES",
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": excluded_country1.pk,
        "erga_omnes_exclusions_formset-1-erga_omnes_exclusion": excluded_country2.pk,
    }
    data.update(exclusions_data)
    set_current_transaction(Transaction.objects.last())
    form = forms.MeasureForm(
        data=data,
        initial={},
        instance=Measure.objects.first(),
        request=session_with_workbasket,
    )
    assert form.is_valid()
    assert form.cleaned_data["exclusions"]
    assert not set(form.cleaned_data["exclusions"]).difference(
        {excluded_country1, excluded_country2},
    )
