import pytest
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import raises_if

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        ({}, True),
        ({"start_date_0": lambda d: d + 1}, True),
        ({"start_date_0": lambda d: d - 1}, False),
        ({"start_date_1": lambda m: m + 1}, True),
        ({"start_date_2": lambda y: y + 1}, True),
    ),
)
def test_regulation_update(new_data, expected_valid, use_update_form):
    with raises_if(ValidationError, not expected_valid):
        use_update_form(factories.UIRegulationFactory(), new_data)
