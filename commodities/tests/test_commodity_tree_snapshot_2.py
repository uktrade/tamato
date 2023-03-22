import pytest

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture()
def prepair_commodity_tree_snapshot():
    transaction = factories.TransactionFactory.create()

    great_great_grand_parent_good = factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=0,
    )

    great_grand_parent_good = factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=1,
    )

    grand_parent_good = factories.GoodsNomenclatureFactory.create(
        item_id="2903690000",
        suffix=10,
        indent__indent=2,
    )

    parent_good = factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=10,
        indent__indent=3,
    )

    child_good_1 = factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=80,
        indent__indent=4,
    )

    child_good_2 = factories.GoodsNomenclatureFactory.create(
        item_id="2903691900",
        suffix=80,
        indent__indent=4,
    )

    commodities = [
        Commodity(
            great_great_grand_parent_good,
            indent_obj=great_great_grand_parent_good.indents.first(),
        ),
        Commodity(
            great_grand_parent_good,
            indent_obj=great_grand_parent_good.indents.first(),
        ),
        Commodity(grand_parent_good, indent_obj=grand_parent_good.indents.first()),
        Commodity(parent_good, indent_obj=parent_good.indents.first()),
        Commodity(child_good_1, indent_obj=child_good_1.indents.first()),
        Commodity(child_good_2, indent_obj=child_good_2.indents.first()),
    ]

    return CommodityTreeSnapshot(
        commodities=commodities,
        moment=SnapshotMoment(transaction=transaction),
    )


class TestCommodityTreeSnapshot:
    def test_init(self, prepair_commodity_tree_snapshot):
        target = prepair_commodity_tree_snapshot
        assert len(target.commodities) == 6
        assert len(target.edges) == 6

    def test_get_parent(self, prepair_commodity_tree_snapshot):
        target = prepair_commodity_tree_snapshot
        assert target.get_parent(target.commodities[4]) == target.commodities[3]

    def test_get_parent_2(self, prepair_commodity_tree_snapshot):
        target = prepair_commodity_tree_snapshot
        assert target.get_parent(target.commodities[5]) == target.commodities[3]

    def test_get_siblings(self, prepair_commodity_tree_snapshot):
        target = prepair_commodity_tree_snapshot
        assert target.commodities[5] in target.get_siblings(target.commodities[4])
        assert target.commodities[4] in target.get_siblings(target.commodities[5])

    def test_get_children(self, prepair_commodity_tree_snapshot):
        target = prepair_commodity_tree_snapshot
        assert target.commodities[5] in target.get_children(target.commodities[3])
        assert target.commodities[4] in target.get_children(target.commodities[3])
