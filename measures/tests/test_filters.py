# tests
# do the filters filter?
# use beautfulsoup - does it look as it should do? Conditional rendering, header changes etc.

from datetime import date
from datetime import timedelta

import pytest

from common.tests import factories
from common.util import TaricDateRange
from measures.filters import MeasureFilter
from measures.models import Measure

pytestmark = pytest.mark.django_db


@pytest.fixture
def queryset():
    # an active measure
    factories.TransactionFactory.create(),
    measure1 = factories.MeasureFactory.create(
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )
    # an inactive measure
    measure2 = factories.MeasureFactory.create(
        valid_between=TaricDateRange(
            date.today() + timedelta(days=-100),
            date.today() + timedelta(days=-99),
        ),
    )
    factories.MeasureFactory.create()
    factories.WorkBasketFactory()


# Does filter by active measures only remove non-active measures?
def test_filter_by_active_measures(queryset):
    # tidy this up
    self = MeasureFilter(data={"measure_filters_modifier": "active"})
    # Check this after adding more measures - may need to include sort
    qs = Measure.objects.all()
    result = MeasureFilter.measures_filter(
        self,
        queryset=qs,
        name="measure_filters_modifier",
        value="active",
    )

    assert len(result) == 1
    assert result[0] == qs[0]
    assert qs[1] not in result


# Check the measures/tests/test_views.py for possible set up hints
# Does filter by measures in workbasket only show measures in current workbasket?
# def test_filter_by_current_workbasket(client, session_workbasket):
#     measure_1 = factories.MeasureFactory.create()
#     measure_2 = factories.MeasureFactory.create()
#     measure_3 = factories.MeasureFactory.create()
#     measure_4 = factories.MeasureFactory.create()
#     measure_5 = factories.MeasureFactory.create()
#     workbasket = factories.WorkBasketFactory()
#     session = client.session
#     self = MeasureFilter(data={"measure_filters_modifier": 'current'})
#     session.update(
#         {
#             "workbasket": {
#                 "id": session_workbasket.pk,
#                 "status": session_workbasket.status,
#                 "title": session_workbasket.title,
#             },
#             "MULTIPLE_MEASURE_SELECTIONS": {
#                 measure_1.pk: True,
#                 measure_2.pk: True,
#                 measure_3.pk: True,
#             }
#         }
#     )
#     session.save()

#     qs = Measure.objects.all()
#     result = MeasureFilter.measures_filter(self, queryset=qs, name="measure_filters_modifier", value="current")
#     print('*'*80, f'{result=}')
#     assert "foo" == "bar"


# Check field ids and name/label are correct
# Does accordion button work?

# Does filter by certificates filter by certificates?
