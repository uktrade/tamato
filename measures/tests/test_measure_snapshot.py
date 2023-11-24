from datetime import date
from datetime import timedelta

import pytest

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from common.models import Transaction
from common.tests import factories
from common.util import TaricDateRange
from measures.snapshots import MeasureSnapshot

pytestmark = pytest.mark.django_db


def test_init(seed_database_with_indented_goods):
    transaction = Transaction.objects.last()
    sn_date = date(2023, 1, 1)
    moment = SnapshotMoment(transaction, sn_date)

    # used the loader to simplify the commodities list generation
    ccl = CommodityCollectionLoader(prefix="2903")
    commodities = ccl.load().commodities
    edges = {}
    ancestors = {}
    descendants = {}
    tree = CommodityTreeSnapshot(commodities, moment, edges, ancestors, descendants)

    target = MeasureSnapshot(moment, tree)

    assert target.moment == moment
    assert target.tree == tree
    assert len(target.tree.descendants) == 4
    assert len(target.tree.edges) == 6
    assert len(target.tree.commodities) == 6
    assert len(target.tree.ancestors) == 6

    assert target.extent == TaricDateRange(date.today())


def test_get_branch_measures(seed_database_with_indented_goods):
    goods = GoodsNomenclature.objects.get(item_id="2903691900")
    commodities_collection = CommodityCollectionLoader(prefix="2903").load().commodities

    target_commodity = None
    for commodity in commodities_collection:
        if commodity.item_id == goods.item_id:
            target_commodity = commodity
    assert target_commodity

    draft_transaction = factories.TransactionFactory.create(draft=True)
    draft_measure = factories.MeasureFactory.create(
        goods_nomenclature=goods,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )

    sn_date = date.today()
    moment = SnapshotMoment(draft_transaction, sn_date)

    tree = CommodityTreeSnapshot(
        commodities_collection,
        moment,
        edges={},
        ancestors={},
        descendants={},
    )

    target = MeasureSnapshot(moment, tree)
    assert target.get_branch_measures(target_commodity).count() == 1
