from datetime import date
from datetime import timedelta

import pytest

from common.tests import factories
from common.util import TaricDateRange
from measures.filters import MeasureFilter
from measures.models import Measure
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_filter_by_live_measures():
    active_measure = factories.MeasureFactory.create(
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )
    measure_starts_today = factories.MeasureFactory.create(
        valid_between=TaricDateRange(date.today()),
    )
    expired_measure = factories.MeasureFactory.create(
        valid_between=TaricDateRange(
            date.today() + timedelta(days=-100),
            date.today() + timedelta(days=-99),
        ),
    )
    future_measure = factories.MeasureFactory.create(
        valid_between=TaricDateRange(
            date.today() + timedelta(days=10),
            date.today() + timedelta(days=99),
        ),
    )
    self = MeasureFilter(data={"measure_filters_modifier": "live"})
    qs = Measure.objects.all()
    result = MeasureFilter.measures_filter(
        self,
        queryset=qs,
        name="measure_filters_modifier",
        value="live",
    )

    assert len(result) == 2
    assert result[0] == qs[0]
    assert expired_measure and future_measure not in result


@pytest.fixture
def queryset(session_workbasket):
    with session_workbasket.new_transaction() as transaction:
        measure_in_workbasket_1 = factories.MeasureFactory.create(
            transaction=transaction,
        )
        measure_in_workbasket_2 = factories.MeasureFactory.create(
            transaction=transaction,
        )

    factories.MeasureFactory.create()
    factories.MeasureFactory.create()


def test_filter_by_current_workbasket(
    valid_user_client,
    session_workbasket: WorkBasket,
    session_request,
):
    session = valid_user_client.session
    session["workbasket"] = {"id": session_workbasket.pk}
    session.save()
    self = MeasureFilter(
        data={"measure_filters_modifier": "current"},
        request=session_request,
    )
    qs = Measure.objects.all()
    result = MeasureFilter.measures_filter(
        self,
        queryset=qs,
        name="measure_filters_modifier",
        value="current",
    )
    assert len(result) == len(session_workbasket.measures)
    assert set(session_workbasket.measures) == set(result)
