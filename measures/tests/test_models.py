from decimal import Decimal

import pytest

from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def test_measure_conditions_list():
    cond = factories.MeasureConditionFactory.create(
        condition_code__code="V",
        component_sequence_number=1,
        duty_amount=Decimal("48.1"),
        monetary_unit__code="EUR",
        condition_measurement=factories.MeasurementFactory.create(
            measurement_unit__code="DTN",
            measurement_unit__abbreviation="100 kg",
            measurement_unit_qualifier=None,
        ),
        action__code="1",
        dependent_measure__additional_code=factories.AdditionalCodeFactory.create(),
    )
    factories.MeasureConditionComponentFactory.create(
        condition=cond,
        duty_expression__sid=1,
        duty_expression__prefix="",
        duty_amount=Decimal("2.5"),
        monetary_unit=None,
    )

    cond = (
        type(cond)
        .objects.latest_approved()
        .with_reference_price_string()
        .with_duty_sentence()
        .get(pk=cond.pk)
    )
    assert cond.reference_price_string == "48.100 EUR DTN"
    assert cond.condition_string == "2.500%"


def test_stringify_measure_condition():
    cond = factories.MeasureConditionFactory.create(
        condition_code__code="V",
        component_sequence_number=11,
        duty_amount=Decimal("0"),
        monetary_unit__code="EUR",
        condition_measurement=factories.MeasurementFactory.create(
            measurement_unit__code="DTN",
            measurement_unit__abbreviation="100 kg",
            measurement_unit_qualifier=None,
        ),
        action__code="1",
        dependent_measure__additional_code=factories.AdditionalCodeFactory.create(),
    )
    factories.MeasureConditionComponentFactory.create(
        condition=cond,
        duty_expression__sid=1,
        duty_expression__prefix="",
        duty_amount=Decimal("2.5"),
        monetary_unit=None,
    )
    factories.MeasureConditionComponentFactory.create(
        condition=cond,
        duty_expression__sid=4,
        duty_expression__prefix="+",
        duty_amount=Decimal("37.8"),
        monetary_unit__code="EUR",
        component_measurement=factories.MeasurementFactory.create(
            measurement_unit__code="DTN",
            measurement_unit__abbreviation="100 kg",
            measurement_unit_qualifier=None,
        ),
    )

    cond = (
        type(cond)
        .objects.latest_approved()
        .with_reference_price_string()
        .with_duty_sentence()
        .get(pk=cond.pk)
    )
    assert cond.reference_price_string == "0.000 EUR DTN"
    assert cond.condition_string == "2.500% + 37.800 EUR / 100 kg"


@pytest.fixture(
    params=(
        lambda d: {
            "valid_between": d.normal,
            "terminating_regulation": factories.RegulationFactory(),
        },
        lambda d: {
            "valid_between": d.no_end,
            "terminating_regulation": None,
        },
    ),
    ids=(
        "has_end_date",
        "has_no_end_date",
    ),
)
def measure_to_terminate(request, date_ranges):
    return factories.MeasureFactory(**request.param(date_ranges))


@pytest.fixture(
    params=(
        lambda d: d.earlier.upper,
        lambda d: d.overlap_normal.upper,
        lambda d: d.later.upper,
    ),
    ids=(
        "before_start",
        "during_validity",
        "after_existing_end",
    ),
)
def termination_date(request, date_ranges):
    return request.param(date_ranges)


def test_measure_termination(workbasket, measure_to_terminate, termination_date):
    terminated_measure = measure_to_terminate.terminate(workbasket, termination_date)

    if terminated_measure.update_type == UpdateType.DELETE:
        assert terminated_measure.valid_between.lower >= termination_date
    else:
        assert terminated_measure.terminating_regulation is not None
        assert terminated_measure.valid_between.upper_inf is False
        assert terminated_measure.valid_between.upper <= termination_date
    terminated_measure.clean()


def test_measure_type_series_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.MeasureTypeSeriesFactory,
        "in_use",
        factories.MeasureTypeFactory,
        "measure_type_series",
    )


def test_measure_type_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.MeasureTypeFactory,
        "in_use",
        factories.MeasureFactory,
        "measure_type",
        leave_measure=True,
    )


def test_measure_action_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.MeasureActionFactory,
        "in_use",
        factories.MeasureConditionComponentFactory,
        "condition__action",
    )
