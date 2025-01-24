import datetime
from unittest.mock import patch

import pytest
from django.forms.models import model_to_dict

from common.forms import SerializableFormMixin
from common.forms import unprefix_formset_data
from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.util import TaricDateRange
from common.validators import ApplicabilityCode
from geo_areas import constants
from geo_areas.validators import AreaCode
from measures import forms
from measures.constants import MEASURE_COMMODITIES_FORMSET_PREFIX
from measures.constants import MEASURE_CONDITIONS_FORMSET_PREFIX
from measures.forms import MeasureConditionsFormSet
from measures.forms import MeasureEndDateForm
from measures.forms import MeasureForm
from measures.forms import MeasureStartDateForm
from measures.models import Measure
from measures.models.tracked_models import DutyExpression
from measures.validators import MeasureExplosionLevel

pytestmark = pytest.mark.django_db

GEO_AREA_FORM_PREFIX = "geographical_area"
COUNTRY_REGION_FORM_PREFIX = "country_region"


@patch("measures.forms.update.diff_components")
def test_diff_components_not_called(
    diff_components,
    measure_form,
    duty_sentence_parser,
):
    with override_current_transaction(Transaction.objects.last()):
        measure_form.request.POST = {}
        measure_form.save(commit=False)

    assert diff_components.called == False


@patch("measures.forms.update.diff_components")
def test_diff_components_called(diff_components, measure_form, duty_sentence_parser):
    measure_form.request.POST = {}
    measure_form.data.update(duty_sentence="6.000%")
    with override_current_transaction(Transaction.objects.last()):
        measure_form.save(commit=False)

    assert diff_components.called == True


def test_measure_conditions_formset_invalid(
    measure_form_data,
    lark_duty_sentence_parser,
):
    """Tests MeasureConditionsFormSet validation."""
    condition_code1 = factories.MeasureConditionCodeFactory.create()
    action1 = factories.MeasureActionFactory.create()

    data = {
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-reference_price": "2%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-action": action1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-applicable_duty": "invalid",
    }
    initial = [
        {
            "applicable_duty": "invalid",
            "condition_code": condition_code1.pk,
            "reference_price": "2%",
            "action": action1.pk,
        },
    ]
    form_data = {**data, **measure_form_data}
    form = MeasureConditionsFormSet(
        data=form_data,
        initial=initial,
    )

    assert not form.is_valid()
    assert "No matching duty expression found" in form.errors[0]["applicable_duty"][0]
    assert (
        "Check the validity period of the duty expression and that you are using the correct prefix."
        in form.errors[0]["applicable_duty"][0]
    )


def test_measure_form_invalid_conditions_data(
    measure_form_data,
    session_request_with_workbasket,
    date_ranges,
    erga_omnes,
    lark_duty_sentence_parser,
):
    """Tests that MeasureForm.is_valid() returns False when
    MeasureConditionsFormSet returns False."""
    condition_code1 = factories.MeasureConditionCodeFactory.create()
    action1 = factories.MeasureActionFactory.create()

    data = {
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-applicable_duty": "invalid",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-reference_price": "2%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-__prefix__-action": action1.pk,
        "submit": "submit",
    }
    form_data = {**data, **measure_form_data}
    measure = Measure.objects.first()
    with override_current_transaction(measure.transaction):
        measure_form = MeasureForm(
            data=form_data,
            initial=form_data,
            instance=measure,
            request=session_request_with_workbasket,
        )

        assert not measure_form.is_valid()
        # formset errors messages are test in view tests


def test_measure_forms_details_valid_data(measure_type):
    start_date = {
        "measure_type": measure_type.pk,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2023,
        "min_commodity_count": 1,
    }
    start_and_end_dates = {
        "measure_type": measure_type.pk,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2023,
        "end_date_0": 2,
        "end_date_1": 2,
        "end_date_2": 2024,
        "min_commodity_count": 99,
    }
    form = forms.MeasureDetailsForm(start_date, prefix="")
    assert form.is_valid()
    form = forms.MeasureDetailsForm(start_and_end_dates, prefix="")
    assert form.is_valid()


def test_measure_forms_regulation_id_valid_data(regulation):
    data = {
        "generating_regulation": regulation.pk,
    }
    form = forms.MeasureRegulationIdForm(data, prefix="")
    assert form.is_valid()


def test_measure_forms_quota_order_number_valid_data(quota_order_number):
    data = {
        "order_number": quota_order_number.pk,
    }
    form = forms.MeasureQuotaOrderNumberForm(data, prefix="")
    assert form.is_valid()
    assert form.cleaned_data["order_number"] == quota_order_number

    empty = {
        "order_number": "",
    }
    form = forms.MeasureQuotaOrderNumberForm(empty, prefix="")
    assert form.is_valid()
    assert form.cleaned_data["order_number"] == None


def test_measure_forms_geo_area_valid_data_erga_omnes(erga_omnes):
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.ERGA_OMNES,
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial=data,
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert form.is_valid()
        assert (
            form.cleaned_data["geo_areas_and_exclusions"][0]["geo_area"] == erga_omnes
        )


def test_measure_forms_geo_area_valid_data_erga_omnes_exclusions(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    formset_prefix = "erga_omnes_exclusions_formset"
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.ERGA_OMNES,
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": geo_area1.pk,
        "erga_omnes_exclusions_formset-1-erga_omnes_exclusion": geo_area2.pk,
        "erga_omnes_exclusions_formset-__prefix__-erga_omnes_exclusion": "",
        "submit": "submit",
    }
    initial = [
        {
            "erga_omnes_exclusion": geo_area1.pk,
        },
        {
            "erga_omnes_exclusion": geo_area2.pk,
        },
    ]
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, formset_prefix: initial},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert form.is_valid()
        assert form.cleaned_data["geo_areas_and_exclusions"][0]["exclusions"] == [
            geo_area1,
            geo_area2,
        ]


def test_measure_forms_geo_area_valid_data_erga_omnes_exclusions_delete(erga_omnes):
    """Test that is_valid returns False when DELETE is in formset data, as per
    FormSet.is_valid()."""
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.ERGA_OMNES,
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": geo_area1.pk,
        "erga_omnes_exclusions_formset-0-DELETE": "1",
        "submit": "submit",
    }
    initial = [
        {
            "erga_omnes_exclusion": geo_area1.pk,
        },
    ]
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, "erga_omnes_exclusions_formset": initial},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_geo_group_exclusions(erga_omnes):
    geo_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.GROUP,
        f"{GEO_AREA_FORM_PREFIX}-geographical_area_group": geo_group.pk,
        "geo_group_exclusions_formset-0-geo_group_exclusion": geo_area1.pk,
        "submit": "submit",
    }
    initial = [
        {
            "geo_group_exclusion": geo_area1.pk,
        },
    ]
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, "geo_group_exclusions_formset": initial},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert form.is_valid()
        assert form.cleaned_data["geo_areas_and_exclusions"][0]["exclusions"] == [
            geo_area1,
        ]


def test_measure_forms_geo_area_valid_data_geo_group_exclusions_delete(erga_omnes):
    """Test that is_valid returns False when DELETE is in formset data, as per
    FormSet.is_valid()."""
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.GROUP,
        "geographical_area_group-geographical_area_group": geo_group.pk,
        "geo_group_exclusions_formset-0-geo_group_exclusion": geo_area1.pk,
        "geo_group_exclusions_formset-0-DELETE": "1",
        "submit": "submit",
    }
    initial = [
        {
            "geo_group_exclusion": geo_area1.pk,
        },
    ]
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, "geo_group_exclusions_formset": initial},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_erga_omnes_exclusions_add(erga_omnes):
    """Test that is_valid returns False when ADD is in formset data, as per
    FormSet.is_valid()."""
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        "geo_area": constants.GeoAreaType.ERGA_OMNES,
        "erga_omnes_exclusions_formset-__prefix__-erga_omnes_exclusion": geo_area1.pk,
        "erga_omnes_exclusions_formset-ADD": "1",
        "submit": "submit",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, "erga_omnes_exclusions_formset": []},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()


def test_measure_forms_geo_area_valid_data_geo_group(erga_omnes):
    geo_group = factories.GeographicalAreaFactory.create(area_code=AreaCode.GROUP)
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.GROUP,
        f"{GEO_AREA_FORM_PREFIX}-geographical_area_group": geo_group.pk,
        "submit": "submit",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial=data,
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert form.is_valid()
        assert form.cleaned_data["geo_areas_and_exclusions"][0]["geo_area"] == geo_group


def test_measure_forms_geo_area_valid_data_countries_submit(erga_omnes):
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.COUNTRY,
        "country_region_formset-0-geographical_area_country_or_region": geo_area1.pk,
        "country_region_formset-1-geographical_area_country_or_region": geo_area2.pk,
        "submit": "submit",
    }
    initial = [
        {"geographical_area_country_or_region": geo_area1.pk},
        {"geographical_area_country_or_region": geo_area2.pk},
    ]
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, "country_region_formset": initial},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert form.is_valid()
        cleaned_data = [
            data["geo_area"] for data in form.cleaned_data["geo_areas_and_exclusions"]
        ]
        assert cleaned_data == [geo_area1, geo_area2]
        # specific country selection should have empty exclusions
        for data in form.cleaned_data["geo_areas_and_exclusions"]:
            assert not data.get("exclusions")


def test_measure_forms_geo_area_valid_data_countries_delete(erga_omnes):
    """Test that is_valid returns False when DELETE is in formset data, as per
    FormSet.is_valid()."""
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.COUNTRY,
        "country_region_formset-0-geographical_area_country_or_region": geo_area1.pk,
        "country_region_formset-1-geographical_area_country_or_region": geo_area2.pk,
        "country_region_formset-DELETE": "on",
    }
    initial = [
        {"geographical_area_country_or_region": geo_area1.pk},
        {"geographical_area_country_or_region": geo_area2.pk},
    ]
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={**data, "country_region_formset": initial},
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()
        # when we submit ADD or DELETE no errors are raised
        assert not form.errors


def test_measure_forms_geo_area_valid_data_countries_add(erga_omnes):
    """Test that is_valid returns False when ADD is in formset data, as per
    FormSet.is_valid()."""
    geo_area1 = factories.GeographicalAreaFactory.create()
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.COUNTRY,
        "country_region_formset-0-geographical_area_country_or_region": geo_area1.pk,
        "country_region_formset-ADD": "1",
        "submit": "submit",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial=data,
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()


def test_measure_forms_geo_area_invalid_data_geo_group_missing_field(erga_omnes):
    """Test that GeoGroupForm raises a field required error when null value is
    passed to geographical_area_group field."""
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.GROUP,
        "geographical_area-geographical_area_group": None,
        "submit": "submit",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial=data,
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()
        assert "A country group is required." in form.errors["geo_area"][0]


def test_measure_forms_geo_area_invalid_data_geo_group_invalid_choice(erga_omnes):
    """Test that GeoGroupForm raises an invalid choice error when passed an area
    whose area_code is not AreaCode.GROUP."""
    geo_area1 = factories.GeographicalAreaFactory.create(area_code=AreaCode.REGION)
    data = {
        f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.GROUP,
        "geographical_area-geographical_area_group": geo_area1.pk,
        "submit": "submit",
    }
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial=data,
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()
        assert (
            "Select a valid choice. That choice is not one of the available choices."
            in form.errors["geo_area"][0]
        )


@pytest.mark.parametrize(
    "data,error",
    [
        (
            {
                f"{GEO_AREA_FORM_PREFIX}-geo_area": constants.GeoAreaType.COUNTRY,
                "country_region_formset-0-geographical_area_country_or_region": "",
                "submit": "submit",
            },
            "Please submit at least 1 form.",
        ),
        (
            {
                f"{GEO_AREA_FORM_PREFIX}-geo_area": "",
                "country_region_formset-0-geographical_area_country_or_region": "",
                "submit": "submit",
            },
            "A Geographical area must be selected",
        ),
    ],
)
def test_measure_forms_geo_area_invalid_data_error_messages(data, error, erga_omnes):
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            data,
            initial={
                **data,
                "country_region_formset": [],
            },
            prefix=GEO_AREA_FORM_PREFIX,
        )
        assert not form.is_valid()
        assert error in form.errors["geo_area"]


def test_measure_quota_origins_form_cleaned_data(date_ranges):
    """Tests that `MeasureQuotaOriginsForm` uses geographical data from selected
    quota origins to set cleaned_data."""

    old_origin = factories.QuotaOrderNumberOriginFactory.create(
        valid_between=date_ranges.earlier,
    )

    order_number = old_origin.order_number

    active_origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=order_number,
        valid_between=date_ranges.normal,
    )

    future_origin = factories.QuotaOrderNumberOriginFactory.create(
        order_number=order_number,
        valid_between=date_ranges.later,
    )
    future_origin_exclusions = (
        factories.QuotaOrderNumberOriginExclusionFactory.create_batch(
            2,
            origin=future_origin,
        )
    )

    form_data = {
        f"selectableobject_{old_origin.pk}": False,
        f"selectableobject_{active_origin.pk}": True,
        f"selectableobject_{future_origin.pk}": True,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureQuotaOriginsForm(
            objects=[old_origin, active_origin, future_origin],
            data=form_data,
        )
        assert form.is_valid()

        expected_cleaned_data = [
            {
                "geo_area": active_origin.geographical_area,
                "exclusions": set(),
            },
            {
                "geo_area": future_origin.geographical_area,
                "exclusions": set(future_origin.excluded_areas.all()),
            },
        ]

        for data in form.cleaned_data["geo_areas_and_exclusions"]:
            data["exclusions"] = set(data["exclusions"])
            assert data in expected_cleaned_data


def test_measure_quota_origins_form_selection_required():
    """Tests that `MeasureQuotaOriginsForm` requires at least one or more quota
    origins to be selected."""

    origin = factories.QuotaOrderNumberOriginFactory.create()

    form_data = {
        f"selectableobject_{origin.pk}": False,
    }

    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureQuotaOriginsForm(
            objects=[origin],
            data=form_data,
        )
        assert not form.is_valid()
        assert "Select one or more quota origins" in form.errors["__all__"]


def test_measure_forms_details_invalid_data():
    data = {
        "measure_type": "foo",
        "start_date_0": 2,
        "start_date_1": 4,
        "start_date_2": 2021,
        "min_commodity_count": 100,
    }
    form = forms.MeasureDetailsForm(data, initial={}, prefix="")
    invalid_choice = [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    invalid_count = [
        "Enter a number between 1 and 99",
    ]
    assert form.errors["measure_type"] == invalid_choice
    assert form.errors["min_commodity_count"] == invalid_count
    assert not form.is_valid()


def test_measure_forms_regulation_id_invalid_data():
    data = {
        "generating_regulation": "bar",
    }
    form = forms.MeasureRegulationIdForm(data, initial={}, prefix="")
    error_string = [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    assert form.errors["generating_regulation"] == error_string
    assert not form.is_valid()


def test_measure_forms_quota_order_number_invalid_data():
    data = {
        "order_number": "foo",
    }
    form = forms.MeasureQuotaOrderNumberForm(data, initial={}, prefix="")
    error_string = [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    assert form.errors["order_number"] == error_string
    assert not form.is_valid()


def test_measure_forms_details_invalid_date_range(measure_type):
    data = {
        "measure_type": measure_type.pk,
        "start_date_0": 1,
        "start_date_1": 1,
        "start_date_2": 2000,
        "end_date_0": 1,
        "end_date_1": 1,
        "end_date_2": 1999,
    }
    form = forms.MeasureDetailsForm(data, initial={}, prefix="")
    # In the real wizard view the prefix will be populated with the name of the form. It's left blank here to make the mock form data simpler
    assert not form.is_valid()
    assert (
        form.errors["__all__"][0]
        == "The date range of the measure can't be outside that of the measure type: [2020-01-01, None) does not contain [2000-01-01, 1999-01-01]"
    )
    assert (
        form.errors["end_date"][0]
        == "The end date must be the same as or after the start date."
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
    "commodity, error_message",
    [
        (
            "test",
            "Select a valid choice. That choice is not one of the available choices.",
        ),
        ("", "Select a commodity code"),
    ],
)
def test_measure_forms_commodity_and_duties_form_invalid_selection(
    commodity,
    error_message,
    lark_duty_sentence_parser,
    date_ranges,
):
    data = {
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-commodity": commodity,
    }
    form = forms.MeasureCommodityAndDutiesForm(
        data,
        prefix=f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0",
        measure_start_date=date_ranges.normal,
    )
    assert not form.is_valid()
    assert error_message in form.errors["commodity"]


def test_measure_forms_commodity_and_duties_form_duties_not_permitted(
    lark_duty_sentence_parser,
):
    """Test that form is invalid when a duty is specified on a commodity but not
    permitted for measure type."""
    measure_type = factories.MeasureTypeFactory.create(
        measure_explosion_level=MeasureExplosionLevel.TARIC,
        measure_component_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )
    form = forms.MeasureCommodityAndDutiesForm(
        data={f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-duties": "123%"},
        prefix=f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0",
        measure_type=measure_type,
    )

    assert not form.is_valid()
    assert (
        f"Duties cannot be added to a commodity for measure type {measure_type}"
        in form.errors["duties"]
    )


@pytest.mark.parametrize(
    "item_id, is_valid",
    [
        ("1234567891", False),
        ("1234567890", False),
        ("1234567800", True),
    ],
)
def test_measure_forms_commodity_and_duties_form_measure_explosion_level(
    item_id,
    is_valid,
    lark_duty_sentence_parser,
):
    """Test that form is invalid when a commodity at 8 digit level or higher is
    selected for an export measure type (measure_explosion_level=8)"""
    commodity = factories.SimpleGoodsNomenclatureFactory.create(item_id=item_id)
    export_measure_type = factories.MeasureTypeFactory.create(
        measure_explosion_level=MeasureExplosionLevel.COMBINED_NOMENCLATURE,
    )
    error_message = f"Commodity must sit at {export_measure_type.measure_explosion_level} digit level or higher for measure type {export_measure_type}"
    data = {
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-commodity": commodity.pk,
    }
    form = forms.MeasureCommodityAndDutiesForm(
        data,
        prefix=f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0",
        measure_type=export_measure_type,
    )
    assert form.is_valid() == is_valid
    if not is_valid:
        assert error_message in form.errors["commodity"]


@pytest.mark.parametrize(
    "data",
    [
        {
            f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-commodity": "",
            f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-duties": "",
            "submit": "submit",
        },
        {},
    ],
)
def test_measure_forms_commodity_and_duties_formset_no_data(
    data,
    lark_duty_sentence_parser,
):
    formset = forms.MeasureCommodityAndDutiesFormSet(
        data=data,
        initial=unprefix_formset_data(MEASURE_CONDITIONS_FORMSET_PREFIX, data),
    )
    assert not formset.is_valid()
    assert "Select one or more commodity codes" in formset.non_form_errors()


def test_measure_forms_commodity_and_duties_formset_valid_data(
    date_ranges,
    lark_duty_sentence_parser,
):
    commodity1, commodity2 = factories.GoodsNomenclatureFactory.create_batch(2)
    data = {
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-commodity": commodity1.pk,
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-duties": "33 GBP/100kg",
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-1-commodity": commodity2.pk,
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-1-duties": "40 GBP/100kg",
        "submit": "submit",
    }
    formset = forms.MeasureCommodityAndDutiesFormSet(
        data=data,
        initial=unprefix_formset_data(MEASURE_COMMODITIES_FORMSET_PREFIX, data),
        min_commodity_count=2,
        measure_start_date=date_ranges.normal.lower,
    )
    assert formset.is_valid()


def test_measure_forms_commodity_and_duties_formset_invalid_data(
    date_ranges,
    lark_duty_sentence_parser,
):
    commodity1, commodity2 = factories.GoodsNomenclatureFactory.create_batch(2)
    invalid_duty_sentence = "1% + 2GBP / m1"
    data = {
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-commodity": commodity1.pk,
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-0-duties": invalid_duty_sentence,
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-1-commodity": commodity2.pk,
        f"{MEASURE_COMMODITIES_FORMSET_PREFIX}-1-duties": "40 GBP/100kg",
        "submit": "submit",
    }
    formset = forms.MeasureCommodityAndDutiesFormSet(
        data=data,
        initial=unprefix_formset_data(MEASURE_COMMODITIES_FORMSET_PREFIX, data),
        min_commodity_count=2,
        measure_start_date=date_ranges.normal.lower,
    )
    assert not formset.is_valid()
    assert (
        "Check the validity period of the measurement unit and that you are using the correct abbreviation (not code)."
        in formset.forms[0].errors["duties"][0]
    )
    assert "No matching measurement unit found" in formset.forms[0].errors["duties"][0]


def test_measure_forms_conditions_form_valid_data(
    lark_duty_sentence_parser,
    date_ranges,
):
    """Tests that MeasureConditionsForm is valid when initialised with minimal
    required fields."""
    certificate = factories.CertificateFactory.create()
    code_with_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=True,
    )
    action = factories.MeasureActionFactory.create()

    data = {
        "condition_code": code_with_certificate.pk,
        "action": action.pk,
        "required_certificate": certificate.pk,
    }
    # MeasureConditionsForm.__init__ expects prefix kwarg for instantiating crispy forms `Layout` object
    form = forms.MeasureConditionsForm(data, prefix="")

    with override_current_transaction(action.transaction):
        assert form.is_valid()


@pytest.mark.parametrize(
    ("code", "valid"),
    (
        ("01", True),
        ("02", True),
        ("03", True),
        ("04", True),
        ("05", False),
    ),
)
def test_measure_forms_conditions_form_actions_validation_skipped(
    code,
    valid,
    date_ranges,
    lark_duty_sentence_parser,
):
    """
    Tests that MeasureConditionsForm is valid when actions 1-4 is used and no
    certificate or reference price is provide but fails for other action codes.

    Initialised with minimal required fields.
    """
    certificate = factories.CertificateFactory.create()
    code_with_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=True,
    )
    action = factories.MeasureActionFactory.create(
        code=code,
    )
    start_date = date_ranges.normal.lower

    data = {
        "condition_code": code_with_certificate.pk,
        "action": action.pk,
        "required_certificate": certificate.pk,
        "reference_price": "11 GBP / 100 kg",
        "start_date_0": start_date.day,
        "start_date_1": start_date.month,
        "start_date_2": start_date.year,
    }
    # MeasureConditionsForm.__init__ expects prefix kwarg for instantiating crispy forms `Layout` object
    form = forms.MeasureConditionsForm(data, prefix="")

    with override_current_transaction(action.transaction):
        if valid:
            assert form.is_valid()
        else:
            assert not form.is_valid()


def test_measure_forms_conditions_wizard_form_valid_data(date_ranges):
    """Tests that MeasureConditionsWizardStepForm is valid when initialised with
    minimal required fields."""
    certificate = factories.CertificateFactory.create()
    factories.MeasureConditionCodeFactory.create()
    code_with_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=True,
    )
    action = factories.MeasureActionFactory.create()

    data = {
        "condition_code": code_with_certificate.pk,
        "action": action.pk,
        "required_certificate": certificate.pk,
    }
    # MeasureConditionsForm.__init__ expects prefix kwarg for instantiating crispy forms `Layout` object
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )

    with override_current_transaction(action.transaction):
        form.is_valid()
        assert form.cleaned_data["condition_code"] == code_with_certificate
        assert form.cleaned_data["action"] == action
        assert form.cleaned_data["required_certificate"] == certificate


def test_measure_forms_conditions_form_invalid_data():
    """Tests that MeasureConditionsForm raises a validation error when a
    required field is missing."""
    action = factories.MeasureActionFactory.create()
    data = {
        "action": action.pk,
    }
    form = forms.MeasureConditionsForm(data, prefix="")

    assert not form.is_valid()
    assert form.errors["condition_code"][0] == "A condition code is required."


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
    assert form.errors["condition_code"][0] == "A condition code is required."


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
        (
            "invalid duty",
            "No matching duty expression found at character 1. \n\nCheck the validity period of the duty expression and that you are using the correct prefix. ",
        ),
        (
            "3.5 % + 11 GBP / 100 kg",
            "A compound duty expression was found at character 7. \n\nCheck that you are entering a single duty amount or a duty amount together with a measurement unit (and measurement unit qualifier if required). ",
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
    assert message in form.errors["reference_price"]


@pytest.mark.parametrize(
    "reference_price, message",
    [
        (
            "invalid duty",
            "No matching duty expression found at character 1. \n\nCheck the validity period of the duty expression and that you are using the correct prefix. ",
        ),
        (
            "3.5 % + 11 GBP / 100 kg",
            "A compound duty expression was found at character 7. \n\nCheck that you are entering a single duty amount or a duty amount together with a measurement unit (and measurement unit qualifier if required). ",
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
    assert message in form.errors["reference_price"]


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
        "reference_price": "11 GBP / 100 kg",
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
        assert "No matching duty expression found" in form.errors["applicable_duty"][0]
        assert (
            "Check the validity period of the duty expression and that you are using the correct prefix"
            in form.errors["applicable_duty"][0]
        )


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
        "reference_price": "11 GBP / 100 kg",
    }
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )

    assert form.is_valid() == is_valid

    if not is_valid:
        assert "No matching duty expression found" in form.errors["applicable_duty"][0]
        assert (
            "Check the validity period of the duty expression and that you are using the correct prefix."
            in form.errors["applicable_duty"][0]
        )


def test_measure_forms_conditions_wizard_applicable_duty_not_permitted():
    """Test that form is invalid when a duty is specified on a condition but not
    permitted for measure type."""
    measure_type = factories.MeasureTypeFactory.create(
        measure_component_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )
    form = forms.MeasureConditionsWizardStepForm(
        data={"applicable_duty": "123%"},
        prefix="",
        measure_type=measure_type,
    )

    assert not form.is_valid()
    assert (
        f"Duties cannot be added to a condition for measure type {measure_type}"
        in form.errors["applicable_duty"]
    )


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
    with override_current_transaction(action.transaction):
        form_expects_certificate.is_valid()
        assert (
            form_expects_certificate.cleaned_data["required_certificate"] == certificate
        )

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
    with override_current_transaction(action.transaction):
        form_expects_certificate.is_valid()
        assert (
            form_expects_certificate.cleaned_data["required_certificate"] == certificate
        )

        form_expects_no_certificate = forms.MeasureConditionsWizardStepForm(
            dict(data, **{"condition_code": code_without_certificate.pk}),
            prefix="",
            measure_start_date=date_ranges.normal,
        )
        assert form_expects_no_certificate.is_valid()
        assert form_expects_no_certificate.cleaned_data["required_certificate"] is None


def test_measure_forms_conditions_wizard_form_invalid_duty(date_ranges):
    """Tests that MeasureConditionsWizardStepForm is invalid when the duty has
    more than 3 decimal places."""
    condition_code = factories.MeasureConditionCodeFactory.create()
    monetary_unit = factories.MonetaryUnitFactory.create()
    factories.MeasurementUnitFactory.create()
    factories.MeasurementUnitQualifierFactory.create()
    factories.MeasureConditionComponentFactory.create()
    action = factories.MeasureActionFactory.create()
    if not DutyExpression.objects.filter(sid=99):
        factories.DutyExpressionFactory.create(sid=99)

    data = {
        "reference_price": f"1.2345 {monetary_unit.code}",
        "action": action.pk,
        "condition_code": condition_code.pk,
    }
    # MeasureConditionsForm.__init__ expects prefix kwarg for instantiating crispy forms `Layout` object
    form = forms.MeasureConditionsWizardStepForm(
        data,
        prefix="",
        measure_start_date=date_ranges.normal,
    )

    with override_current_transaction(action.transaction):
        assert not form.is_valid()
        assert (
            "The reference price cannot have more than 3 decimal places."
            in form.errors["reference_price"]
        )


def test_measure_form_valid_data(erga_omnes, session_request_with_workbasket):
    """Test that MeasureForm.is_valid returns True when passed required fields
    and geographical_area and sid fields in cleaned data."""
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
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureForm(
            data=data,
            initial={},
            instance=Measure.objects.first(),
            request=session_request_with_workbasket,
        )
        assert form.is_valid()
        assert (
            form.cleaned_data["geographical_area"].pk
            == data["country_region-geographical_area_country_or_region"]
        )
        assert form.cleaned_data["sid"] == measure.sid


@pytest.mark.parametrize("initial_option", [("ERGA_OMNES"), ("GROUP"), ("COUNTRY")])
def test_measure_form_initial_data_geo_area(
    initial_option,
    erga_omnes,
    session_request_with_workbasket,
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
        request=session_request_with_workbasket,
    )
    assert form.initial["geo_area"] == geo_area_to_choice[measure.geographical_area]


def test_measure_form_cleaned_data_geo_exclusions_group(
    erga_omnes,
    session_request_with_workbasket,
):
    """Test that MeasureForm accepts geo_area form group data and returns
    excluded countries in cleaned data."""
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
        "submit": "submit",
    }
    data.update(exclusions_data)
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureForm(
            data=data,
            initial=data,
            instance=Measure.objects.first(),
            request=session_request_with_workbasket,
        )
        assert form.is_valid()
        assert form.cleaned_data["exclusions"] == [excluded_country1, excluded_country2]


def test_measure_form_cleaned_data_geo_exclusions_erga_omnes(
    erga_omnes,
    session_request_with_workbasket,
):
    """Test that MeasureForm accepts geo_area form erga omnes data and returns
    excluded countries in cleaned data."""
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
        "submit": "submit",
    }
    data.update(exclusions_data)
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureForm(
            data=data,
            initial=data,
            instance=Measure.objects.first(),
            request=session_request_with_workbasket,
        )
        assert form.is_valid()
        assert form.cleaned_data["exclusions"] == [excluded_country1, excluded_country2]


def test_measure_start_date_validation_fail():
    valid_between = TaricDateRange(
        lower=datetime.date(2000, 1, 1),
        upper=datetime.date(2100, 1, 1),
    )
    selected_measures = factories.MeasureFactory.create_batch(
        3,
        valid_between=valid_between,
    )
    form = MeasureStartDateForm(
        data={
            "start_date_0": "01",
            "start_date_1": "01",
            "start_date_2": "2200",
        },
        selected_measures=selected_measures,
    )

    assert not form.is_valid()
    assert (
        "The start date cannot be after the end date: Start date 01/01/2200 does not start before 01/01/2100"
        in form.errors["__all__"]
    )


def test_measure_end_date_validation_fail():
    valid_between = TaricDateRange(
        lower=datetime.date(2000, 1, 1),
        upper=datetime.date(2100, 1, 1),
    )
    selected_measures = factories.MeasureFactory.create_batch(
        3,
        valid_between=valid_between,
    )
    form = MeasureEndDateForm(
        data={
            "end_date_0": "01",
            "end_date_1": "01",
            "end_date_2": "1999",
        },
        selected_measures=selected_measures,
    )

    assert not form.is_valid()
    assert (
        "The end date cannot be before the start date: Start date 01/01/2000 does not start before 01/01/1999"
        in form.errors["__all__"]
    )


def test_measure_end_date_form_no_end_date():
    """Tests that `MeasureEndDateForm` allows an empty end date value and sets
    the cleaned data value to `None`."""
    selected_measures = factories.MeasureFactory.create_batch(3)
    form = MeasureEndDateForm(
        data={},
        selected_measures=selected_measures,
    )
    assert form.is_valid()
    assert form.cleaned_data["end_date"] == None


def test_measure_forms_footnotes_valid():
    footnote = factories.FootnoteFactory.create()
    data = {
        "footnote": footnote.pk,
    }
    form = forms.MeasureFootnotesForm(data, prefix="")
    assert form.is_valid()
    assert form.cleaned_data["footnote"] == footnote


def test_measure_forms_footnotes_invalid_footnote_choice():
    data = {
        "footnote": "foo",
    }
    form = forms.MeasureFootnotesForm(data, prefix="")
    assert form.errors["footnote"] == [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    assert not form.is_valid()


def test_measure_forms_footnotes_invalid_duplicate_footnote():
    footnote = factories.FootnoteFactory.create()
    data = {
        "form-0-footnote": footnote.pk,
        "form-1-footnote": footnote.pk,
    }
    initial = [
        {
            "footnote": footnote.pk,
        },
        {
            "footnote": footnote.pk,
        },
    ]
    formset = forms.MeasureFootnotesFormSet(data, initial=initial)
    assert not formset.is_valid()
    assert (
        "The same footnote cannot be added more than once" in formset.non_form_errors()
    )


def measure_conditions_different_actions_data():
    condition_code1 = factories.MeasureConditionCodeFactory.create()
    action1, action2 = factories.MeasureActionFactory.create_batch(2)

    return {
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-reference_price": "2%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-action": action1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-reference_price": "3%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-action": action2.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
    }


def measure_conditions_duplicate_price_data():
    condition_code1 = factories.MeasureConditionCodeFactory.create()
    action1 = factories.MeasureActionFactory.create()
    return {
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-reference_price": "2%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-action": action1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-reference_price": "2%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-action": action1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
    }


def measure_conditions_incorrect_order_data():
    condition_code1 = factories.MeasureConditionCodeFactory.create(code="A")
    condition_code2 = factories.MeasureConditionCodeFactory.create(code="B")
    action1, action2 = factories.MeasureActionFactory.create_batch(2)

    return {
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-condition_code": condition_code2.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-reference_price": "2%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-action": action1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-condition_code": condition_code1.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-reference_price": "3%",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-action": action2.pk,
    }


@pytest.mark.parametrize(
    ("data", "error_expected", "error_message"),
    (
        (
            measure_conditions_different_actions_data,
            True,
            "All conditions of the same condition code must have the same resulting action, except for the negative action code pair.",
        ),
        (
            measure_conditions_duplicate_price_data,
            True,
            "The same price cannot be added more than once to the same condition code.",
        ),
        (
            measure_conditions_incorrect_order_data,
            True,
            "All conditions codes must be added in alphabetical order.",
        ),
    ),
)
def test_measure_formset_conditions_invalid(
    data,
    error_expected,
    error_message,
    date_ranges,
    duty_sentence_parser,
):
    """Test for all formset level errors across the form in Measure
    conditions."""

    # setup
    data = data()
    # execution
    formset = forms.MeasureConditionsWizardStepFormSet(
        data,
        initial=unprefix_formset_data(MEASURE_CONDITIONS_FORMSET_PREFIX, data),
        form_kwargs={"measure_start_date": date_ranges.normal},
    )

    # validation
    if error_expected:
        assert not formset.is_valid()
        assert error_message in formset.non_form_errors()
    else:
        assert formset.is_valid()


def test_measure_formset_invalid_duplicate_certs(date_ranges, duty_sentence_parser):
    certificate = factories.CertificateFactory.create()
    code_with_certificate = factories.MeasureConditionCodeFactory(
        accepts_certificate=True,
    )
    action = factories.MeasureActionFactory.create()
    data = {
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-condition_code": code_with_certificate.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-required_certificate": certificate.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-action": action.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-0-applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-condition_code": code_with_certificate.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-required_certificate": certificate.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-action": action.pk,
        f"{MEASURE_CONDITIONS_FORMSET_PREFIX}-1-applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
    }
    formset2 = forms.MeasureConditionsWizardStepFormSet(
        data,
        initial=unprefix_formset_data(MEASURE_CONDITIONS_FORMSET_PREFIX, data),
        prefix="",
        form_kwargs={"measure_start_date": date_ranges.normal},
    )
    with override_current_transaction(action.transaction):
        assert not formset2.is_valid()
        assert (
            "The same certificate cannot be added more than once to the same condition code."
            in formset2.non_form_errors()
        )


def test_measure_formset_conditions_action_field_queryset(
    date_ranges,
):
    """Tests measure actions select field for create & edit measure conditons
    Create measure conditions should not return negative action codes While Edit
    measure conditions should return all aciton codes."""
    (
        positive_action,
        negative_action,
        single_action,
    ) = factories.MeasureActionFactory.create_batch(3)

    factories.MeasureActionPairFactory(
        positive_action=positive_action,
        negative_action=negative_action,
    )

    form = forms.MeasureConditionsWizardStepForm(
        data={},
        prefix=MEASURE_CONDITIONS_FORMSET_PREFIX,
        measure_start_date=date_ranges.normal,
        instance=None,
    )

    assert form
    assert positive_action in form["action"].field.queryset
    assert single_action in form["action"].field.queryset
    assert negative_action not in form["action"].field.queryset

    edit_form = forms.MeasureConditionsForm(
        data={},
        prefix=MEASURE_CONDITIONS_FORMSET_PREFIX,
        instance=None,
    )

    assert edit_form
    assert positive_action in edit_form["action"].field.queryset
    assert single_action in edit_form["action"].field.queryset
    assert negative_action in edit_form["action"].field.queryset


@pytest.mark.parametrize(
    "commodities_data, conditions_data, expected_valid",
    [
        ([{"duties": "123%"}], [{"applicable_duty": ""}], True),
        ([{"duties": ""}], [{"applicable_duty": "321%"}], True),
        ([{"duties": ""}], [{"applicable_duty": ""}], False),
    ],
)
def test_measure_review_form_validates_components_applicability_mandatory(
    commodities_data,
    conditions_data,
    expected_valid,
):
    """Test that form validates at least one duty is specified on either a
    commodity or a condition where component is mandatory for measure type."""
    measure_type = factories.MeasureTypeFactory.create(
        measure_component_applicability_code=ApplicabilityCode.MANDATORY,
    )
    form = forms.MeasureReviewForm(
        data={},
        measure_type=measure_type,
        commodities_data=commodities_data,
        conditions_data=conditions_data,
    )
    assert form.is_valid() == expected_valid
    if not expected_valid:
        assert (
            f"You must specify at least one duty on either a commodity or a condition for measure type {measure_type}"
            in form.errors["__all__"]
        )


def test_measure_review_form_validates_components_applicability_exclusivity(
    measure_type,
):
    """Test that the form is invalid when a duty has been specified on both a
    commodity and a condition."""
    form = forms.MeasureReviewForm(
        data={},
        measure_type=measure_type,
        commodities_data=[{"duties": "123%"}],
        conditions_data=[{"applicable_duty": "321%"}],
    )
    assert not form.is_valid()
    assert (
        "A duty cannot be specified on both commodities and conditions"
        in form.errors["__all__"]
    )


def test_measure_geographical_area_exclusions_form_valid_choice():
    """Tests that `MeasureGeographicalAreaExclusionsForm` is valid when an
    available geographical area is selected."""
    geo_area = factories.GeographicalAreaFactory.create()
    data = {
        "excluded_area": geo_area.pk,
    }
    with override_current_transaction(geo_area.transaction):
        form = forms.MeasureGeographicalAreaExclusionsForm(data)
        assert form.is_valid()
        assert form.cleaned_data["excluded_area"] == geo_area


def test_measure_geographical_area_exclusions_form_invalid_choice():
    """Tests that `MeasureGeographicalAreaExclusionsForm` raises an raises an
    invalid choice error when an unavailable geographical area is selected."""
    data = {
        "excluded_area": "geo_area",
    }
    form = forms.MeasureGeographicalAreaExclusionsForm(data)
    assert not form.is_valid()
    assert form.errors["excluded_area"] == [
        "Select a valid choice. That choice is not one of the available choices.",
    ]


def test_get_serializable_data_keys():
    """Test that the SerializableFormMixin.get_serializable_data_keys() behaves
    correctly and as expected."""

    class TestSerializableForm(SerializableFormMixin):
        def __init__(self, data):
            self.data = data

    serializable_data = {
        "valid_key": "",
        "another_valid_key": "",
    }
    ignorable_data = {
        "csrfmiddlewaretoken": "",
        "measure_create_wizard-current_step": "",
        "submit": "",
        "some_kind_of_autocomplete": "",
        "test-formset-TOTAL_FORMS": 1,
        "test-formset-INITIAL_FORMS": 1,
        "test-formset-MIN_NUM_FORMS": "0",
        "test-formset-MAX_NUM_FORMS": "1000",
    }
    form_data = {**ignorable_data, **serializable_data}
    test_form = TestSerializableForm(data=form_data)

    assert test_form.get_serializable_data_keys() == list(serializable_data.keys())


"""The following tests check the serialization and deserialization capabilities
of the CreateMeasure form wizard forms. Forms have been grouped by type as they
require different parameters, so can not be tested in one parametrize block."""


@pytest.mark.parametrize(
    "form_class, form_data",
    [
        (
            forms.MeasureDetailsForm,
            "measure_details_form_data",
        ),
        (
            forms.MeasureRegulationIdForm,
            "measure_regulation_id_form_data",
        ),
        (
            forms.MeasureAdditionalCodeForm,
            "measure_additional_code_form_data",
        ),
        (
            forms.MeasureQuotaOrderNumberForm,
            "measure_quota_order_number_form_data",
        ),
    ],
    ids=[
        "measure_details_form",
        "regulation_id_form",
        "additional_code_form",
        "quota_order_number_form",
    ],
)
def test_simple_measure_forms_serialize_deserialize(form_class, form_data, request):
    """Test that the CreateMeasure simple forms that use the
    SerializableFormMixin behave correctly and as expected."""

    # Check the forms are valid on data submission
    form_data = request.getfixturevalue(form_data)
    form = form_class(form_data)
    assert form.is_valid()

    # Create the serialized data
    serialized_data = form.serializable_data()

    # Make a form from serialized data
    deserialized_form = form_class(data=serialized_data)

    # Check the form is the right type, valid, and the data that went in is the same that comes out
    assert type(deserialized_form) == form_class
    assert deserialized_form.is_valid()
    assert deserialized_form.data == form_data


@pytest.mark.parametrize(
    "form_class, form_data",
    [
        (
            forms.MeasureQuotaOriginsForm,
            "measure_quota_order_number_origin_form_data",
        ),
    ],
    ids=[
        "quota_order_number_origin_form",
    ],
)
def test_selectableobjects_measure_forms_serialize_deserialize(
    form_class,
    form_data,
    request,
):
    """Test that the CreateMeasure selectableobjects forms that use the
    SerializableFormMixin behave correctly and as expected."""

    form_data = request.getfixturevalue(form_data)
    objects = form_data["objects"]
    data = form_data["data"]

    form_kwargs = {"objects": objects}

    with override_current_transaction(Transaction.objects.last()):
        # Check the forms are valid on data submission
        form = form_class(
            initial={},
            objects=objects,
            data=data,
        )
        assert form.is_valid()

        # Create the serialized data
        serialized_data = form.serializable_data()
        serialized_form_kwargs = form.serializable_init_kwargs(form_kwargs)

        # Deserialize the kwargs
        deserialized_form_kwargs = form.deserialize_init_kwargs(serialized_form_kwargs)

        # Make a form from serialized data
        deserialized_form = form_class(data=serialized_data, **deserialized_form_kwargs)

        # Check the form is the right type, valid, and the data that went in is the same that comes out
        assert type(deserialized_form) == form_class
        assert deserialized_form.is_valid()
        assert deserialized_form.data == data


@pytest.mark.parametrize(
    "form_class, form_data",
    [
        (
            forms.MeasureConditionsWizardStepFormSet,
            "measure_conditions_form_data",
        ),
        (
            forms.MeasureFootnotesFormSet,
            "measure_footnotes_form_data",
        ),
        (
            forms.MeasureCommodityAndDutiesFormSet,
            "measure_commodities_and_duties_form_data",
        ),
    ],
    ids=[
        "conditions_form",
        "footnotes",
        "commodities",
    ],
)
def test_formset_measure_forms_serialize_deserialize(
    form_class,
    form_data,
    request,
    duty_sentence_parser,
):
    """Test that the CreateMeasure formset forms that use the
    SerializableFormMixin behave correctly and as expected."""
    form_data = request.getfixturevalue(form_data)
    data = form_data["data"]
    kwargs = form_data["kwargs"]

    # Check the forms are valid on data submission
    form_set = form_class(
        data=data,
        **kwargs,
    )
    assert form_set.is_valid()

    # Create the serialized data
    serializable_form_data = form_set.serializable_data()
    serializable_form_kwargs = form_set.serializable_init_kwargs(kwargs)

    # Deserialize the kwargs
    deserialized_form_kwargs = form_set.deserialize_init_kwargs(
        serializable_form_kwargs,
    )
    # Make a form from serialized data.Check the form is the right type, valid, and the data that went in is the same that comes out
    deserialized_form_set = form_class(
        data=serializable_form_data,
        **deserialized_form_kwargs,
    )
    assert deserialized_form_set.is_valid()
    assert type(deserialized_form_set) == form_class
    assert deserialized_form_set.get_serializable_data_keys() == list(data.keys())
    for key in deserialized_form_set.get_serializable_data_keys():
        if key in data.keys():
            assert form_set.data[key] == data[key]


@pytest.mark.parametrize(
    "form_data",
    [
        ("measure_geo_area_erga_omnes_form_data"),
        ("measure_geo_area_erga_omnes_exclusions_form_data"),
        ("measure_geo_area_geo_group_form_data"),
        ("measure_geo_area_geo_group_exclusions_form_data"),
    ],
    ids=[
        "erga-omnes",
        "erga-omnes-exclusions",
        "geo-group",
        "geo-group-exclusions",
    ],
)
def test_measure_forms_geo_area_serialize_deserialize(form_data, request):
    form_data = request.getfixturevalue(form_data)
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaForm(
            form_data,
        )
        assert form.is_valid()

        serializable_form_data = form.serializable_data()

        deserialized_form = forms.MeasureGeographicalAreaForm(
            data=serializable_form_data,
        )
        assert deserialized_form.is_valid()
        assert type(deserialized_form) == forms.MeasureGeographicalAreaForm
        assert deserialized_form.data == form.data


@pytest.mark.parametrize(
    "form_class, form_data_fixture, has_form_kwargs",
    [
        (
            forms.MeasureStartDateForm,
            "measure_edit_start_date_form_data",
            True,
        ),
        (
            forms.MeasureEndDateForm,
            "measure_edit_end_date_form_data",
            True,
        ),
        (
            forms.MeasureQuotaOrderNumberForm,
            "measure_quota_order_number_form_data",
            False,
        ),
        (
            forms.MeasureRegulationForm,
            "measure_edit_regulation_form_data",
            True,
        ),
        (
            forms.MeasureDutiesForm,
            "measure_edit_duties_form_data",
            True,
        ),
    ],
    ids=[
        "measure_edit_start_date_form",
        "measure_edit_end_date_form",
        "measure_edit_quota_order_number_form",
        "measure_edit_regulation_form",
        "measure_edit_duties_form",
    ],
)
def test_simple_measure_edit_forms_serialize_deserialize(
    form_class,
    form_data_fixture,
    has_form_kwargs,
    date_ranges,
    request,
    duty_sentence_parser,
):
    """Test that the EditMeasure simple forms that use the SerializableFormMixin
    behave correctly and as expected."""
    """Test that the EditMeasure simple forms that use the SerializableFormMixin
    behave correctly and as expected."""

    # Create some measures to apply this data to, for the kwargs
    quota_order_number = factories.QuotaOrderNumberFactory()
    regulation = factories.RegulationFactory.create()
    selected_measures = factories.MeasureFactory.create_batch(
        4,
        valid_between=date_ranges.normal,
        order_number=quota_order_number,
        generating_regulation=regulation,
    )

    # Check the forms are valid on data submission
    form_data = request.getfixturevalue(form_data_fixture)
    form_kwarg_data = {}

    if has_form_kwargs:
        form_kwarg_data = {
            "selected_measures": selected_measures,
        }

    form = form_class(form_data, **form_kwarg_data)
    assert form.is_valid()

    # Create the serialized data
    serialized_data = form.serializable_data()
    serialized_data_kwargs = {}

    if has_form_kwargs:
        serialized_data_kwargs = form.serializable_init_kwargs(form_kwarg_data)

    # Deserialize the kwargs
    deserialized_form_kwargs = form.deserialize_init_kwargs(
        serialized_data_kwargs,
    )

    # Make a form from serialized data.Check the form is the right type, valid, and the data that went in is the same that comes out
    deserialized_form = form_class(
        data=serialized_data,
        **deserialized_form_kwargs,
    )

    # Check the form is the right type, valid, and the data that went in is the same that comes out
    assert type(deserialized_form) == form_class
    assert deserialized_form.is_valid()
    assert deserialized_form.data == form_data


def test_measure_edit_forms_geo_area_exclusions_serialize_deserialize():
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()

    form_data = {"form-0-excluded_area": geo_area1, "form-1-excluded_area": geo_area2}
    with override_current_transaction(Transaction.objects.last()):
        form = forms.MeasureGeographicalAreaExclusionsFormSet(
            form_data,
        )
        assert form.is_valid()

        serializable_form_data = form.serializable_data()

        deserialized_form = forms.MeasureGeographicalAreaExclusionsFormSet(
            data=serializable_form_data,
        )
        assert deserialized_form.is_valid()
        assert type(deserialized_form) == forms.MeasureGeographicalAreaExclusionsFormSet
        assert deserialized_form.data == form.data
