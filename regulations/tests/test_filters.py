import pytest

from common.tests.factories import UIDraftRegulationFactory
from common.tests.factories import UIRegulationFactory
from regulations.filters import RegulationFilter

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("regulation_factory", "search_filter", "value", "expected_result"),
    [
        (
            lambda: UIRegulationFactory.create(
                regulation_group__group_id="PRF",
            ),
            "regulation_group",
            "PRF",
            1,
        ),
        (
            lambda: UIDraftRegulationFactory.create(),
            "regulation_usage",
            "C",
            1,
        ),
        (lambda: UIRegulationFactory.create(), "approved", True, 1),
        (
            lambda: UIDraftRegulationFactory.create(),
            "regulation_usage",
            "X",
            0,
        ),
        (lambda: UIRegulationFactory.create(), "approved", False, 0),
    ],
)
def test_regulation_filter_filters_queryset(
    regulation_factory,
    search_filter,
    value,
    expected_result,
    session_request,
):
    """Test that `RegulationFilter` filters queryset by search filter value."""
    regulation = regulation_factory()
    filter = RegulationFilter(data={search_filter: [value]}, request=session_request)
    result = filter.qs
    assert len(result) == expected_result
    if result:
        assert regulation in result
