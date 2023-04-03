from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError

from common.tests import factories
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
        transaction=cond.transaction,
    )

    cond = (
        type(cond)
        .objects.latest_approved()
        .with_reference_price_string()
        .get(pk=cond.pk)
    )
    assert cond.reference_price_string == "48.100 EUR / 100 kg"
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
        transaction=cond.transaction,
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
        transaction=cond.transaction,
    )

    cond = (
        type(cond)
        .objects.latest_approved()
        .with_reference_price_string()
        .get(pk=cond.pk)
    )
    assert cond.reference_price_string == "0.000 EUR / 100 kg"
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
        factories.MeasureConditionFactory,
        "action",
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
    ("GoodsNomenclatureFactory"),
    (factories.GoodsNomenclatureFactory, None),
)
def test_commodity_code_change_performs_DELETE_and_CREATE(GoodsNomenclatureFactory):
    goods_nomenclature = (
        GoodsNomenclatureFactory() if GoodsNomenclatureFactory else None
    )
    measure = factories.MeasureFactory.create(goods_nomenclature=goods_nomenclature)
    new_nomenclature = factories.GoodsNomenclatureFactory()

    assert Measure.objects.count() == 1

    factories.MeasureFactory.create(
        version_group=measure.version_group,
        update_type=UpdateType.UPDATE,
        goods_nomenclature=new_nomenclature,
    )

    deleted_measure = Measure.objects.filter(update_type=UpdateType.DELETE).first()
    created_measure = Measure.objects.filter(
        goods_nomenclature=new_nomenclature,
        update_type=UpdateType.CREATE,
    ).first()

    assert deleted_measure is not None
    assert created_measure is not None
    assert Measure.objects.count() == 3


@pytest.fixture(
    params=(
        ("normal", "no_end", "normal"),
        ("no_end", "normal", "normal"),
        ("no_end", "no_end", "no_end"),
    ),
    ids=(
        "normal",
        "effective_normal",
        "no_end",
    ),
)
def regulation_date_ranges(request, date_ranges):
    valid_between, effective_valid_between, expected_range = request.param
    return {
        "valid_between": getattr(date_ranges, valid_between),
        "effective_end_date": getattr(date_ranges, effective_valid_between).upper,
    }, getattr(date_ranges, expected_range)


@pytest.fixture(
    params=(
        (factories.BaseRegulationFactory, ""),
        (factories.ModifiedBaseRegulationFactory, "amendment__enacting_regulation__"),
        (factories.ModificationRegulationFactory, "amendment__target_regulation__"),
        (factories.ModificationRegulationFactory, ""),
    ),
    ids=(
        "base_with_own_end",
        "base_with_ended_modification",
        "modification_with_ended_base",
        "modification_with_own_end",
    ),
)
def measure_regulation(request, regulation_date_ranges):
    factory, attr = request.param
    dates, expected_range = regulation_date_ranges
    data = {(attr + field): value for field, value in dates.items()}
    model = factory(**data)
    return model, expected_range


@pytest.mark.parametrize(
    ("measure_dates"),
    ("normal", "no_end"),
    ids=("implicit", "explicit"),
)
def test_effective_valid_between(measure_regulation, measure_dates, date_ranges):
    regulation, regulation_range = measure_regulation
    measure_range = getattr(date_ranges, measure_dates)
    measure: Measure = factories.MeasureFactory.create(
        generating_regulation=regulation,
        valid_between=measure_range,
    )

    expected_dates = (
        measure_range
        if regulation_range.upper_is_greater(measure_range)
        else regulation_range
    )
    assert measure.effective_valid_between == expected_dates
    assert measure.effective_end_date == expected_dates.upper


def test_measure_action_pair():
    action_1 = factories.MeasureActionFactory.create()
    action_2 = factories.MeasureActionFactory.create()
    action_pair = factories.MeasureActionPairFactory.create(
        positive_action=action_1,
        negative_action=action_2,
    )
    assert action_pair


def test_measure_action_pair_invalid():
    """Tests that invalid measure pairs cannot be created."""

    action_1 = factories.MeasureActionFactory.create()
    action_2 = factories.MeasureActionFactory.create()
    action_3 = factories.MeasureActionFactory.create()
    action_4 = factories.MeasureActionFactory.create()

    # cannot pair with itself
    with pytest.raises(ValidationError):
        factories.MeasureActionPairFactory.create(
            positive_action=action_1,
            negative_action=action_1,
        )

    factories.MeasureActionPairFactory.create(
        positive_action=action_1,
        negative_action=action_2,
    )

    # cannot reuse positive action
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            factories.MeasureActionPairFactory.create(
                positive_action=action_1,
                negative_action=action_4,
            )

    # cannot reuse negative action
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            factories.MeasureActionPairFactory.create(
                positive_action=action_3,
                negative_action=action_2,
            )

    # cannot use already used negative action in positive
    with pytest.raises(ValidationError):
        factories.MeasureActionPairFactory.create(
            positive_action=action_2,
            negative_action=action_4,
        )

    # cannot use already used positive action in negative
    with pytest.raises(ValidationError):
        factories.MeasureActionPairFactory.create(
            positive_action=action_3,
            negative_action=action_1,
        )
