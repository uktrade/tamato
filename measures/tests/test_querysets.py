from typing import Dict
from typing import List
from typing import Tuple

import factory
import pytest

from common.tests import factories

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
def test_duty_sentence_generation(
    component_factory: factory.django.DjangoModelFactory,
    model_factory: factory.django.DjangoModelFactory,
    field: str,
    reversible_duty_sentence_data: Tuple[str, List[Dict]],
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
    for kwargs in component_data:
        component_factory(
            **{field: model},
            **kwargs,
        )

    test_instance = model_factory._meta.model.objects.with_duty_sentence().get()
    assert test_instance.duty_sentence == expected
