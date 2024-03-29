import pytest

from commodities.filters import CommodityFilter
from commodities.filters import GoodsNomenclatureFilterBackend
from commodities.models.orm import GoodsNomenclature
from common.filters import CurrentWorkBasketMixin
from common.filters import TamatoFilterMixin
from common.filters import type_choices
from common.tests.factories import GoodsNomenclatureDescriptionFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import TestModel2Factory
from common.tests.models import TestModel2

pytestmark = pytest.mark.django_db


@pytest.fixture(params=(0, 1, 10))
def choice_inputs(request):
    return [TestModel2Factory() for _ in range(request.param)]


def test_type_choices(choice_inputs):
    get_choices = type_choices(TestModel2.objects.all())

    values = [choice.value for choice in get_choices()]
    custom_sids = [choice_input.custom_sid for choice_input in choice_inputs]

    assert values == custom_sids


def test_search_queryset_returns_partial_match():
    nomenclature = GoodsNomenclatureFactory.create(sid="131")
    qs = GoodsNomenclature.objects.all()
    result = TamatoFilterMixin().search_queryset(qs, "13")

    assert nomenclature in result


def test_search_queryset_returns_case_insensitive():
    nomenclature = GoodsNomenclatureDescriptionFactory.create(
        description="Red roses",
    ).described_goods_nomenclature
    qs = GoodsNomenclature.objects.all()
    result = GoodsNomenclatureFilterBackend().search_queryset(qs, "RED")

    assert nomenclature in result


def test_filter_by_current_workbasket_mixin(
    valid_user_client,
    user_workbasket,
    session_request,
):
    with user_workbasket.new_transaction() as transaction:
        commodity_in_workbasket_1 = GoodsNomenclatureFactory.create(
            transaction=transaction,
        )
        commodity_in_workbasket_2 = GoodsNomenclatureFactory.create(
            transaction=transaction,
        )
    commodity_not_in_workbasket_1 = GoodsNomenclatureFactory.create()
    commodity_not_in_workbasket_2 = GoodsNomenclatureFactory.create()

    qs = GoodsNomenclature.objects.all()

    self = CommodityFilter(
        CurrentWorkBasketMixin,
        request=session_request,
    )

    res = CurrentWorkBasketMixin.filter_work_basket(
        self=self,
        queryset=qs,
        name="current_work_basket",
        value=True,
    )

    for model in res:
        assert type(model) == self._meta.model

    assert commodity_in_workbasket_1 in res
    assert commodity_in_workbasket_2 in res
    assert commodity_not_in_workbasket_1 not in res
    assert commodity_not_in_workbasket_2 not in res
