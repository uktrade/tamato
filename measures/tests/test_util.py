import pytest

from common.tests import factories
from common.validators import UpdateType
from measures import util
from measures.models import MeasureComponent

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "value, conversion, expected",
    [
        ("20.000", 2, "40.000"),
        ("1.000", 0.83687, "0.830"),
    ],
)
def test_eur_to_gbp_conversion(value, conversion, expected):
    assert util.convert_eur_to_gbp(value, conversion) == expected


def test_diff_components_update(
    workbasket,
    duty_sentence_parser,
    percent_or_amount,
):
    original_component = factories.MeasureComponentFactory.create(
        duty_amount=9.000,
        duty_expression=percent_or_amount,
    )
    new_measure = original_component.component_measure.new_version(
        original_component.transaction.workbasket,
    )
    util.diff_components(
        new_measure,
        "8.000%",
        original_component.component_measure.valid_between.lower,
        workbasket,
        new_measure.transaction,
        MeasureComponent,
        "component_measure",
    )
    components = new_measure.components.approved_up_to_transaction(
        workbasket.current_transaction,
    )

    assert components.count() == 1

    new_component = components.last()

    assert new_component.update_type == UpdateType.UPDATE
    assert new_component.version_group == original_component.version_group
    assert new_component.component_measure == new_measure
    assert new_component.transaction == workbasket.current_transaction
    assert new_component.duty_amount == 8.000


def test_diff_components_update_multiple(
    workbasket,
    duty_sentence_parser,
    percent_or_amount,
    plus_percent_or_amount,
    monetary_units,
    measurement_units,
):
    component_1 = factories.MeasureComponentFactory.create(
        duty_amount=12.000,
        duty_expression=percent_or_amount,
    )
    component_2 = factories.MeasureComponentFactory.create(
        component_measure=component_1.component_measure,
        duty_amount=253.000,
        duty_expression=plus_percent_or_amount,
        monetary_unit=monetary_units["GBP"],
        component_measurement__measurement_unit=measurement_units[1],
    )
    new_measure = component_1.component_measure.new_version(
        component_1.transaction.workbasket,
    )
    util.diff_components(
        component_2.component_measure,
        "13.000% + 254.000 GBP / 100 kg",
        component_1.component_measure.valid_between.lower,
        workbasket,
        new_measure.transaction,
        MeasureComponent,
        "component_measure",
    )
    components = component_1.component_measure.components.approved_up_to_transaction(
        workbasket.current_transaction,
    )

    assert components.count() == 2

    first = components.filter(
        duty_expression__sid=component_1.duty_expression.sid,
    ).first()
    second = components.filter(
        duty_expression__sid=component_2.duty_expression.sid,
    ).first()

    assert components.count() == 2
    assert first.duty_amount == 13.000
    assert second.duty_amount == 254.000
    assert components.first().transaction == components.last().transaction


def test_diff_components_create(workbasket, duty_sentence_parser):
    measure = factories.MeasureFactory.create()
    util.diff_components(
        measure,
        "8.000%",
        measure.valid_between.lower,
        workbasket,
        measure.transaction,
        MeasureComponent,
        "component_measure",
    )
    components = measure.components.approved_up_to_transaction(
        workbasket.current_transaction,
    )

    assert components.count() == 1

    new_component = components.last()

    assert new_component.update_type == UpdateType.CREATE
    assert new_component.component_measure == measure
    assert new_component.transaction == workbasket.current_transaction
    assert new_component.duty_amount == 8.000


def test_diff_components_delete(
    workbasket,
    duty_sentence_parser,
    percent_or_amount,
):
    component = factories.MeasureComponentFactory.create(
        duty_amount=9.000,
        duty_expression=percent_or_amount,
    )
    new_measure = component.component_measure.new_version(
        component.transaction.workbasket,
    )
    util.diff_components(
        component.component_measure,
        "",
        component.component_measure.valid_between.lower,
        workbasket,
        new_measure.transaction,
        MeasureComponent,
        "component_measure",
    )
    components = component.component_measure.components.approved_up_to_transaction(
        workbasket.current_transaction,
    )

    assert components.count() == 0

    deleted = MeasureComponent.objects.filter(
        component_measure=component.component_measure,
        update_type=UpdateType.DELETE,
    )

    assert deleted.exists()
    assert deleted.first().transaction == workbasket.current_transaction
