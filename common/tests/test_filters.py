import pytest

from common.filters import type_choices
from common.tests.factories import TestModel2Factory
from common.tests.models import TestModel2

pytestmark = pytest.mark.django_db


@pytest.fixture(params=(0, 1, 10))
def choice_inputs(request):
    return [TestModel2Factory() for _ in range(request.param)]


def test_type_choices(choice_inputs):
    get_choices = type_choices(TestModel2.objects.all())
    choices = get_choices()

    assert len(choices) == len(choice_inputs)
    for input, output in zip(choice_inputs, choices):
        assert output.value == input.custom_sid
