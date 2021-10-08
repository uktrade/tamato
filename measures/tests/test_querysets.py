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

pytestmark = pytest.mark.django_db


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
    for kwargs in reorder(component_data):
        component_factory(
            **{field: model},
            **kwargs,
        )

    test_instance = model_factory._meta.model.objects.with_duty_sentence().get()
    assert test_instance.duty_sentence == expected


def test_get_measures_in_effect(date_ranges):
    effective_measure = factories.MeasureFactory.create()
    ineffective_measure = factories.MeasureFactory.create(
        valid_between=date_ranges.later,
    )
    qs = Measure.objects.get_measures_in_effect()

    assert effective_measure in qs
    assert ineffective_measure not in qs


def test_get_measures_not_in_effect(date_ranges):
    effective_measure = factories.MeasureFactory.create()
    ineffective_measure = factories.MeasureFactory.create(
        valid_between=date_ranges.later,
    )
    qs = Measure.objects.get_measures_not_in_effect()

    assert effective_measure not in qs
    assert ineffective_measure in qs


def test_get_measures_no_longer_in_effect(date_ranges):
    effective_measure = factories.MeasureFactory.create()
    future_measure = factories.MeasureFactory.create(valid_between=date_ranges.later)
    measure_no_longer_in_effect = factories.MeasureFactory.create(
        valid_between=date_ranges.earlier,
    )
    qs = Measure.objects.get_measures_no_longer_in_effect()

    assert effective_measure not in qs
    assert future_measure not in qs
    assert measure_no_longer_in_effect in qs


def test_get_measures_not_yet_in_effect(date_ranges):
    effective_measure = factories.MeasureFactory.create()
    future_measure = factories.MeasureFactory.create(valid_between=date_ranges.later)
    measure_no_longer_in_effect = factories.MeasureFactory.create(
        valid_between=date_ranges.earlier,
    )
    qs = Measure.objects.get_measures_not_yet_in_effect()

    assert effective_measure not in qs
    assert future_measure in qs
    assert measure_no_longer_in_effect not in qs


def test_get_measures_current():
    previous_measure = factories.MeasureFactory.create()
    current_measure = factories.MeasureFactory.create(
        version_group=previous_measure.version_group,
    )
    qs = Measure.objects.get_measures_current()

    assert previous_measure not in qs
    assert current_measure in qs


def test_get_measures_not_current():
    previous_measure = factories.MeasureFactory.create()
    current_measure = factories.MeasureFactory.create(
        version_group=previous_measure.version_group,
    )
    qs = Measure.objects.get_measures_not_current()

    assert previous_measure in qs
    assert current_measure not in qs


def test_get_measures_current_and_in_effect(date_ranges):
    previous_measure = factories.MeasureFactory.create()
    current_effective_measure = factories.MeasureFactory.create(
        version_group=previous_measure.version_group,
    )
    ineffective_measure = factories.MeasureFactory.create(
        valid_between=date_ranges.earlier,
    )

    qs = Measure.objects.get_measures_current_and_in_effect()

    assert previous_measure not in qs
    assert current_effective_measure in qs
    assert ineffective_measure not in qs
