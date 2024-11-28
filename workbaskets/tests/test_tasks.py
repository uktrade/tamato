import pytest

from common.models import Transaction
from common.tests import factories
from workbaskets.tasks import get_comm_codes_with_missing_measures

pytestmark = pytest.mark.django_db


@pytest.fixture
def measure_type103():
    return factories.MeasureTypeFactory.create(sid=103)


def test_get_comm_codes_with_missing_measures_new_comm_code_fail(
    erga_omnes,
    date_ranges,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
    )

    comm_codes_with_missing_measures = get_comm_codes_with_missing_measures(
        new_commodity.transaction.pk,
        [new_commodity.pk],
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
        pref.transaction.pk,
        [new_commodity.pk],
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
        new_commodity.transaction.pk,
        [new_commodity.pk],
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
        tx.pk,
        [new_commodity.pk],
    )
    assert not comm_codes_with_missing_measures
