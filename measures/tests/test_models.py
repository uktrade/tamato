from decimal import Decimal

import pytest

from common.tests import factories
from common.tests.util import Dates
from common.validators import UpdateType
from measures.models import Measure

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


@pytest.mark.parametrize(
    "factory",
    [
        factories.MeasureTypeSeriesFactory,
        factories.MeasurementUnitFactory,
        factories.MeasurementUnitQualifierFactory,
        factories.MeasurementFactory,
        factories.MonetaryUnitFactory,
        factories.DutyExpressionFactory,
        factories.MeasureTypeFactory,
        factories.AdditionalCodeTypeMeasureTypeFactory,
        factories.MeasureConditionCodeFactory,
        factories.MeasureActionFactory,
        factories.MeasureFactory,
        factories.MeasureComponentFactory,
        factories.MeasureConditionFactory,
        factories.MeasureConditionComponentFactory,
        factories.MeasureExcludedGeographicalAreaFactory,
        factories.FootnoteAssociationMeasureFactory,
    ],
)
def test_measure_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(
        factory,
    )


@pytest.mark.parametrize(
    ("export_refund_sid"),
    (None, 123),
)
def test_copy_measure_doesnt_add_export_refund_sids(export_refund_sid):
    """Although export refund is defined as a SID, it should not be incremented
    or added if it is not present."""
    measure = factories.MeasureFactory.create(
        export_refund_nomenclature_sid=export_refund_sid,
    )
    copy = measure.copy(factories.ApprovedTransactionFactory())

    assert copy.export_refund_nomenclature_sid == export_refund_sid


@pytest.mark.parametrize(
    ("excluded_measures_kwargs", "included_measure_kwargs", "measure_method"),
    [
        ([{"valid_between": Dates().later}], {}, Measure.get_measures_in_effect),
        ([{}], {"valid_between": Dates().later}, Measure.get_measures_not_in_effect),
        (
            [{}, {"valid_between": Dates().later}],
            {"valid_between": Dates().earlier},
            Measure.get_measures_no_longer_in_effect,
        ),
        (
            [{}, {"valid_between": Dates().earlier}],
            {"valid_between": Dates().later},
            Measure.get_measures_not_yet_in_effect,
        ),
    ],
)
def test_get_effective_measures_class_methods(
    excluded_measures_kwargs,
    included_measure_kwargs,
    measure_method,
):
    excluded_measures = [
        factories.MeasureFactory.create(**kwargs) for kwargs in excluded_measures_kwargs
    ]
    included_measure = factories.MeasureFactory.create(**included_measure_kwargs)
    qs = measure_method()

    for measure in excluded_measures:
        assert measure not in qs

    assert included_measure in qs


@pytest.mark.parametrize(
    ("current_excluded", "measure_method"),
    [
        (False, Measure.get_measures_current),
        (True, Measure.get_measures_not_current),
        (False, Measure.get_measures_current_and_in_effect),
    ],
)
def test_get_current_measures_class_methods(
    current_excluded,
    measure_method,
    date_ranges,
):
    previous_measure = factories.MeasureFactory.create()
    current_measure = factories.MeasureFactory.create(
        version_group=previous_measure.version_group,
    )
    qs = measure_method()

    if current_excluded:
        assert previous_measure in qs
        assert current_measure not in qs
    else:
        assert previous_measure not in qs
        assert current_measure in qs

    if measure_method == Measure.get_measures_current_and_in_effect:
        ineffective_measure = factories.MeasureFactory.create(
            valid_between=date_ranges.earlier,
        )
        assert ineffective_measure not in qs
