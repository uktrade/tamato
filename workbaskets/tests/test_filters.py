import pytest

from common.tests.factories import WorkBasketFactory
from workbaskets.filters import WorkBasketAutoCompleteFilterBackEnd
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_workbasket_autocomplete_filter_backend():
    """Tests that WorkBasketAutoCompleteFilterBackEnd filters workbaskets by
    exact and partial match of search term."""
    workbasket1 = WorkBasketFactory.create(
        pk=1111,
        title="wb1",
        reason="samedescription",
    )
    workbasket2 = WorkBasketFactory.create(
        pk=2222,
        title="wb2",
        reason="samedescription",
    )
    queryset = WorkBasket.objects.all()

    filter = WorkBasketAutoCompleteFilterBackEnd()
    results = filter.search_queryset(queryset=queryset, search_term=str(workbasket1.pk))
    assert workbasket1 in results
    assert workbasket2 not in results

    results = filter.search_queryset(queryset=queryset, search_term="same")
    assert workbasket1 in results
    assert workbasket2 in results
