import pytest

from commodities.filters import CommodityFilter
from commodities.models.orm import GoodsNomenclature
from common.tests import factories

pytestmark = pytest.mark.django_db


def test_commodity_filter_footnotes(rf):
    factories.GoodsNomenclatureFactory.create_batch(10)
    commodity1 = factories.GoodsNomenclatureFactory.create()
    commodity2 = factories.GoodsNomenclatureFactory.create()
    commodity3 = factories.GoodsNomenclatureFactory.create()
    footnote1 = factories.FootnoteFactory.create()
    factories.FootnoteFactory.create()
    factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote1,
        goods_nomenclature=commodity1,
    )
    factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        associated_footnote=footnote1,
        goods_nomenclature=commodity2,
    )
    queryset = GoodsNomenclature.objects.all()
    filter = CommodityFilter(queryset=queryset, request=rf)
    filtered = filter.footnotes_count(queryset, None, True)
    assert filtered.count() == 2
    assert commodity1 in filtered
    assert commodity2 in filtered
    assert commodity3 not in filtered


# @pytest.fixture
# def queryset(session_workbasket):
#     with session_workbasket.new_transaction() as transaction:
#         commodity_in_workbasket_1 = factories.GoodsNomenclatureFactory.create(transaction=transaction)
#         commodity_in_workbasket_2 = factories.GoodsNomenclatureFactory.create(transaction=transaction)

#     commodity_not_in_workbasket_1 = factories.GoodsNomenclatureFactory.create(transaction=transaction)
#     commodity_not_in_workbasket_2 = factories.GoodsNomenclatureFactory.create(transaction=transaction)

# def test_current_workbasket_mixin_commodities(valid_user_client, session_workbasket, session_request, rf):
#     session = valid_user_client.session
#     session["workbasket"] = {"id": session_workbasket.pk}
#     session.save()

#     self = CommodityFilter(data={"current_work_basket": "current"})

#     qs = GoodsNomenclature.objects.all()

#     result = CommodityFilter(
#         self,
#         queryset=qs,
#         request=rf
#     )
#     print(f'{result=}')
#     assert 0
