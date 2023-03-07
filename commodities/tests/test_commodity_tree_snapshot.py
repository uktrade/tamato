from datetime import date
from datetime import timedelta

import pytest

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from common.tests import factories
from common.util import TaricDateRange
from measures.models import Measure

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


def test_get_dependent_measures_ignores_archived_measures(
    seed_database_with_indented_goods,
):
    # setup data with archived workbasket and published workbasket
    goods = GoodsNomenclature.objects.all().get(item_id="2903691900")
    commodities_collection = CommodityCollectionLoader(prefix="2903").load()

    for commodity in commodities_collection.commodities:
        if commodity.item_id == "2903691900":
            pass

    archived_transaction = factories.TransactionFactory.create(archived=True)
    archived_measure = factories.MeasureFactory.create(
        transaction=archived_transaction,
        goods_nomenclature=goods,
    )

    published_transaction = factories.TransactionFactory.create(published=True)
    published_measure = factories.MeasureFactory.create(goods_nomenclature=goods)

    # call get_dependent_measures and check archived measure does not exist in results

    target = CommodityTreeSnapshot(
        commodities=commodities_collection.commodities,
        moment=SnapshotMoment(transaction=published_measure.transaction),
    )

    assert target.get_dependent_measures().count() == 1
    assert Measure.objects.all().count() == 2


def test_get_dependent_measures_works_with_wonky_archived_measure(
    seed_database_with_indented_goods,
):
    # setup data with archived workbasket and published workbasket
    goods = GoodsNomenclature.objects.all().get(item_id="2903691900")
    commodities_collection = CommodityCollectionLoader(prefix="2903").load()

    target_commodity = None

    for commodity in commodities_collection.commodities:
        if commodity.item_id == "2903691900":
            target_commodity = commodity

    archived_transaction = factories.TransactionFactory.create(archived=True)
    old_regulation = factories.RegulationFactory.create(
        valid_between=TaricDateRange(date(1982, 1, 1), date(1982, 12, 31)),
    )
    wonky_archived_measure = factories.MeasureFactory.create(
        transaction=archived_transaction,
        goods_nomenclature=goods,
        generating_regulation=old_regulation,
        terminating_regulation=old_regulation,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )

    published_transaction = factories.TransactionFactory.create(published=True)
    published_measure = factories.MeasureFactory.create(
        goods_nomenclature=goods,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )

    # call get_dependent_measures and check archived measure does not exist in results

    target = CommodityTreeSnapshot(
        commodities=commodities_collection.commodities,
        moment=SnapshotMoment(
            transaction=published_measure.transaction,
            date=date.today(),
        ),
    )

    assert target.get_dependent_measures().count() == 1
    assert Measure.objects.all().count() == 2
    assert wonky_archived_measure.generating_regulation == old_regulation
    assert target_commodity in commodities_collection.commodities
    assert target_commodity in target.commodities
