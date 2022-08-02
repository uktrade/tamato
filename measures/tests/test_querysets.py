from datetime import date
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Sequence
from typing import Tuple

import factory
import pytest

from common.tests import factories
from measures.models import Measure
from measures.models import MeasureCondition
from measures.validators import validate_duties

pytestmark = pytest.mark.django_db


def create_duty_components(
    component_factory,
    component_data,
    field_name,
    model,
):
    components = []
    for kwargs in component_data:
        component = component_factory(
            **{field_name: model},
            transaction=model.transaction,
            **kwargs,
        )
        components.append(component)
    return components


@pytest.mark.parametrize(
    "component_factory,model_factory,field",
    (
        (
            factories.MeasureComponentFactory,
            factories.MeasureFactory,
            "component_measure",
        ),
        (
            factories.MeasureConditionComponentFactory,
            factories.MeasureConditionFactory,
            "condition",
        ),
    ),
    ids=(
        factories.MeasureFactory._meta.model.__name__,
        factories.MeasureConditionFactory._meta.model.__name__,
    ),
)
@pytest.mark.parametrize(
    ("reorder"),
    (
        lambda x: x,
        lambda x: reversed(x),
    ),
    ids=(
        "normal",
        "reversed",
    ),
)
def test_duty_sentence_generation(
    component_factory: factory.django.DjangoModelFactory,
    model_factory: factory.django.DjangoModelFactory,
    field: str,
    reversible_duty_sentence_data: Tuple[str, List[Dict]],
    reorder: Callable[[Sequence[Any]], Sequence[Any]],
):
    """
    Links components to the same model and tests the resulting single duty
    sentence.

    First a single instance of the model under test is created and then from
    each component_data dict we build a component instance. We use the passed
    field name to correctly link it to the model instance. This indirection
    allows us to use the same test for Measures and MeasureConditions.
    """
    expected, component_data = reversible_duty_sentence_data

    model = model_factory()
    create_duty_components(component_factory, component_data, field, model)

    test_instance = model_factory._meta.model.objects.get()
    assert test_instance.duty_sentence == expected


@pytest.mark.parametrize(
    "component_factory,model_factory,field_name",
    (
        (
            factories.MeasureComponentFactory,
            factories.MeasureFactory,
            "component_measure",
        ),
        (
            factories.MeasureConditionComponentFactory,
            factories.MeasureConditionFactory,
            "condition",
        ),
    ),
    ids=(
        factories.MeasureFactory._meta.model.__name__,
        factories.MeasureConditionFactory._meta.model.__name__,
    ),
)
def test_duty_sentence_with_history(
    component_factory: factory.django.DjangoModelFactory,
    model_factory: factory.django.DjangoModelFactory,
    field_name: str,
    duty_sentence_x_2_data: List[Tuple[str, List[Dict]]],
):
    """Sets up a history of model instances (Measure or MeasureCondition) and
    linked components and test that the correct duty sentence is available via
    the object's duty_sentence property throughout the instance's history."""
    model_qs = model_factory._meta.model.objects.all()

    # Create model instance and associate it with duty components.
    model_1 = model_factory()
    expected, component_data = duty_sentence_x_2_data[0]
    create_duty_components(component_factory, component_data, field_name, model_1)
    test_instance = model_qs.get_latest_version(sid=model_1.sid)
    assert test_instance.duty_sentence == expected

    # Create a new version of the model and associate it with new duty components.
    model_2 = model_1.new_version(model_1.transaction.workbasket)
    expected, component_data = duty_sentence_x_2_data[1]
    create_duty_components(component_factory, component_data, field_name, model_2)
    test_instance = model_qs.get_latest_version(sid=model_2.sid)
    assert test_instance.duty_sentence == expected

    # Create a new version of the model but don't update duty components.
    model_3 = model_2.new_version(model_2.transaction.workbasket)
    test_instance = model_qs.get_latest_version(sid=model_3.sid)
    assert test_instance.duty_sentence == expected

    # Go back in history to the model's fist version to check its duty_sentence.
    expected, component_data = duty_sentence_x_2_data[0]
    test_instance = model_qs.get_first_version(sid=model_1.sid)
    assert test_instance.duty_sentence == expected


def test_measures_not_in_effect(date_ranges):
    """Tests that only measures whose validity_field_name
    (`db_effective_valid_between` in this case) does not contain the selected
    date are returned."""
    effective_measure = factories.MeasureFactory.create()
    ineffective_measure = factories.MeasureFactory.create(
        valid_between=date_ranges.later,
    )
    qs = Measure.objects.filter().not_in_effect(date.today())

    assert effective_measure not in qs
    assert ineffective_measure in qs


def test_get_measures_no_longer_in_effect(date_ranges):
    """Tests that only measures whose validity_field_name
    (`db_effective_valid_between` in this case) does not contain the selected
    date and does not fall after the selected date are returned."""
    effective_measure = factories.MeasureFactory.create()
    future_measure = factories.MeasureFactory.create(valid_between=date_ranges.later)
    measure_no_longer_in_effect = factories.MeasureFactory.create(
        valid_between=date_ranges.earlier,
    )
    qs = Measure.objects.filter().no_longer_in_effect(date.today())

    assert effective_measure not in qs
    assert future_measure not in qs
    assert measure_no_longer_in_effect in qs


def test_get_measures_not_yet_in_effect(date_ranges):
    """Tests that only measures whose validity_field_name
    (`db_effective_valid_between` in this case) begins after the selected date
    are returned."""
    effective_measure = factories.MeasureFactory.create()
    future_measure = factories.MeasureFactory.create(valid_between=date_ranges.later)
    measure_no_longer_in_effect = factories.MeasureFactory.create(
        valid_between=date_ranges.earlier,
    )
    qs = Measure.objects.filter().not_yet_in_effect(date.today())

    assert effective_measure not in qs
    assert future_measure in qs
    assert measure_no_longer_in_effect not in qs


def test_get_measures_not_current():
    """Tests that only measures which are not the latest approved version are
    returned."""
    previous_measure = factories.MeasureFactory.create()
    current_measure = factories.MeasureFactory.create(
        version_group=previous_measure.version_group,
    )
    qs = Measure.objects.filter().not_current()

    assert previous_measure in qs
    assert current_measure not in qs


@pytest.mark.parametrize(
    "create_kwargs, expected",
    [
        ({"duty_amount": None}, ""),
        ({"duty_amount": 8.000, "monetary_unit": None}, "8.000%"),
        ({"duty_amount": 33.000, "monetary_unit__code": "GBP"}, "33.000 GBP"),
    ],
)
def test_with_reference_price_string_no_measurement(
    create_kwargs,
    expected,
    duty_sentence_parser,
):
    """Tests that different combinations of duty_amount and monetary_unit
    produce the expect reference_price_string and that this string represents a
    valid duty sentence."""
    condition = factories.MeasureConditionFactory.create(**create_kwargs)
    qs = MeasureCondition.objects.with_reference_price_string()
    price_condition = qs.first()

    assert price_condition.reference_price_string == expected
    validate_duties(
        price_condition.reference_price_string,
        condition.dependent_measure.valid_between.lower,
    )


@pytest.mark.parametrize(
    "measurement_kwargs, condition_kwargs, expected",
    [
        (
            {
                "measurement_unit__abbreviation": "100 kg",
                "measurement_unit_qualifier__abbreviation": "lactic.",
            },
            {"duty_amount": 33.000, "monetary_unit__code": "GBP"},
            "33.000 GBP / 100 kg / lactic.",
        ),
        (
            {
                "measurement_unit__abbreviation": "100 kg",
                "measurement_unit_qualifier": None,
            },
            {"duty_amount": 33.000, "monetary_unit__code": "GBP"},
            "33.000 GBP / 100 kg",
        ),
        (
            {
                "measurement_unit__abbreviation": "100 kg",
                "measurement_unit_qualifier__abbreviation": "lactic.",
            },
            {
                "duty_amount": None,
                "monetary_unit": None,
            },
            "",
        ),
        (
            {
                "measurement_unit__abbreviation": "100 kg",
                "measurement_unit_qualifier": None,
            },
            {
                "duty_amount": None,
                "monetary_unit": None,
            },
            "",
        ),
    ],
)
def test_with_reference_price_string_measurement(
    measurement_kwargs,
    condition_kwargs,
    expected,
    duty_sentence_parser,
):
    """
    Tests that different combinations of duty_amount, monetary_unit, and
    measurement produce the expect reference_price_string and that this string
    represents a valid duty sentence.

    The final two scenarios record the fact that this queryset, unlike
    ``duty_sentence_string``, does not support supplementary units and these
    expressions should evaluate to an empty string.
    """
    condition_measurement = factories.MeasurementFactory.create(**measurement_kwargs)
    condition = factories.MeasureConditionFactory.create(
        condition_measurement=condition_measurement, **condition_kwargs
    )
    qs = MeasureCondition.objects.with_reference_price_string()
    price_condition = qs.first()

    assert price_condition.reference_price_string == expected
    validate_duties(
        price_condition.reference_price_string,
        condition.dependent_measure.valid_between.lower,
    )
