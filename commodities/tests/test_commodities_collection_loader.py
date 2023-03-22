import pytest

from commodities.models.dc import CommodityCollectionLoader
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture()
def seed_database_with_indented_goods():
    transaction = factories.TransactionFactory.create()

    factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=0,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=1,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903690000",
        suffix=10,
        indent__indent=2,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=10,
        indent__indent=3,
    )

    child_good_1 = factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=80,
        indent__indent=4,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903691900",
        suffix=80,
        indent__indent=4,
    )

    # duplicate indent for child_good_1, with indent of 3
    child_good_1.indents.first().copy(indent=3, transaction=transaction)


class TestCommodityCollectionLoader:
    def test_load(self, seed_database_with_indented_goods):
        target = CommodityCollectionLoader(prefix="29")
        commodity_collection = target.load()
        assert len(commodity_collection.commodities) == 6

    def test_indent_count_and_value(self, seed_database_with_indented_goods):
        # check that the latest indent is being applied from the load function in the commodity_collection, the fixture
        # creates an additional indent record on 2903691100 which should be latest, all details for indent are the same
        # except the trackedmodel_ptr_id is greater and the indent value is 3 not 4
        target = CommodityCollectionLoader(prefix="29")
        commodity_collection = target.load()
        comm = commodity_collection.commodities[4]

        # there should be 2 indents
        assert len(comm.obj.indents.all()) == 2
        assert len(comm.obj.indents.latest_approved()) == 2
        # latest indent should be 3
        assert comm.indent == 3
        # verify that the tm id ordering is as expected
        assert (
            comm.obj.indents.latest_approved().get(indent=3).trackedmodel_ptr_id
            > comm.obj.indents.latest_approved().get(indent=4).trackedmodel_ptr_id
        )
