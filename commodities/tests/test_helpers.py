from datetime import date
from datetime import timedelta

import pytest

from commodities.helpers import get_comm_codes_with_missing_measures
from commodities.helpers import get_measures_on_declarable_commodities
from commodities.models.orm import GoodsNomenclature
from common.models.transactions import Transaction
from common.tests import factories
from common.util import TaricDateRange

pytestmark = pytest.mark.django_db


@pytest.fixture
def measure_type103():
    return factories.MeasureTypeFactory.create(sid=103)


def test_modc_query(seed_database_with_indented_goods):
    chapter_commodity = (
        GoodsNomenclature.objects.all().filter(item_id="2903000000").first()
    )
    child_commodity = GoodsNomenclature.objects.all().get(item_id="2903690000")
    measure1 = factories.MeasureFactory.create(
        goods_nomenclature=chapter_commodity,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )
    measure2 = factories.MeasureFactory.create(
        goods_nomenclature=child_commodity,
        valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
    )

    result = get_measures_on_declarable_commodities(measure2.transaction, "2903691900")
    assert result.count() == 2
    assert measure1 in result
    assert measure2 in result


def test_get_comm_codes_with_missing_measures_new_comm_code_fail(
    erga_omnes,
    date_ranges,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
    )

    comm_codes_with_missing_measures = get_comm_codes_with_missing_measures(
        new_commodity.transaction,
        [new_commodity],
        date=date.today(),
    )
    assert comm_codes_with_missing_measures == [
        new_commodity,
    ]


def test_get_comm_codes_with_missing_measures_new_comm_code_142_fail(erga_omnes):
    measure_type142 = factories.MeasureTypeFactory.create(sid=103)
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
    )
    pref = factories.MeasureFactory.create(
        measure_type=measure_type142,
        goods_nomenclature=new_commodity,
        transaction=workbasket.new_transaction(),
    )
    comm_codes_with_missing_measures = get_comm_codes_with_missing_measures(
        pref.transaction,
        [new_commodity],
        date=date.today(),
    )
    assert comm_codes_with_missing_measures == [
        new_commodity,
    ]


def test_get_comm_codes_with_missing_measures_new_comm_code_99_pass(
    erga_omnes,
    measure_type103,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
        item_id="9900000000",
    )
    comm_codes_with_missing_measures = get_comm_codes_with_missing_measures(
        new_commodity.transaction,
        [new_commodity],
        date=date.today(),
    )
    assert not comm_codes_with_missing_measures


def test_get_comm_codes_with_missing_measures_new_comm_code_103_pass(
    erga_omnes,
    measure_type103,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
    )
    mfn = factories.MeasureFactory.create(
        measure_type=measure_type103,
        goods_nomenclature=new_commodity,
        geographical_area=erga_omnes,
        transaction=workbasket.new_transaction(),
    )
    tx = Transaction.objects.last()
    comm_codes_with_missing_measures = get_comm_codes_with_missing_measures(
        tx,
        [new_commodity],
        date=date.today(),
    )
    assert not comm_codes_with_missing_measures


def test_get_comm_codes_with_missing_measures_new_comm_code_mfn_pass(
    erga_omnes,
    measure_type103,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
    )
    mfn = factories.MeasureFactory.create(
        measure_type=measure_type103,
        goods_nomenclature=new_commodity,
        geographical_area=erga_omnes,
        transaction=workbasket.new_transaction(),
    )
    tx = Transaction.objects.last()
    comm_codes_with_missing_measures = get_comm_codes_with_missing_measures(
        tx,
        [new_commodity],
        date=date.today(),
    )
    assert not comm_codes_with_missing_measures
