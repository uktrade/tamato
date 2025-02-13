import pytest

from checks.models import MissingMeasureCommCode
from checks.tests.factories import MissingMeasuresCheckFactory
from common.models import Transaction
from common.tests import factories
from workbaskets.tasks import create_missing_measure_comm_codes

pytestmark = pytest.mark.django_db


@pytest.fixture
def measure_type103():
    return factories.MeasureTypeFactory.create(sid=103)


def test_create_missing_measure_comm_codes_new_comm_code_fail(
    erga_omnes,
    date_ranges,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
    )

    missing_measures_check = MissingMeasuresCheckFactory.create(workbasket=workbasket)

    create_missing_measure_comm_codes(
        new_commodity.transaction.pk,
        [new_commodity.pk],
        10,
        missing_measures_check,
    )
    failed_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
        successful=False,
    )
    assert new_commodity in [m.commodity for m in failed_comm_codes]


def test_create_missing_measure_comm_codes_new_comm_code_142_fail(erga_omnes):
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
    missing_measures_check = MissingMeasuresCheckFactory.create(workbasket=workbasket)
    create_missing_measure_comm_codes(
        pref.transaction.pk,
        [new_commodity.pk],
        10,
        missing_measures_check,
    )
    failed_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
        successful=False,
    )
    assert new_commodity in [m.commodity for m in failed_comm_codes]


def test_create_missing_measure_comm_codes_new_comm_code_99_pass(
    erga_omnes,
    measure_type103,
):
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
        item_id="9900000000",
    )
    missing_measures_check = MissingMeasuresCheckFactory.create(
        workbasket=workbasket,
        successful=True,
    )
    create_missing_measure_comm_codes(
        new_commodity.transaction.pk,
        [new_commodity.pk],
        10,
        missing_measures_check,
    )
    failed_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
        successful=False,
    )
    assert not failed_comm_codes


def test_create_missing_measure_comm_codes_new_comm_code_103_pass(
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
    missing_measures_check = MissingMeasuresCheckFactory.create(workbasket=workbasket)
    create_missing_measure_comm_codes(
        tx.pk,
        [new_commodity.pk],
        10,
        missing_measures_check,
    )
    failed_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
        successful=False,
    )
    assert not failed_comm_codes


def test_create_missing_measure_comm_codes_ended_comm_code_pass(
    erga_omnes,
    date_ranges,
):
    measure_type142 = factories.MeasureTypeFactory.create(sid=103)
    workbasket = factories.WorkBasketFactory.create()
    new_commodity = factories.GoodsNomenclatureFactory.create(
        transaction=workbasket.new_transaction(),
        valid_between=date_ranges.earlier,
    )
    pref = factories.MeasureFactory.create(
        measure_type=measure_type142,
        goods_nomenclature=new_commodity,
        transaction=workbasket.new_transaction(),
    )
    missing_measures_check = MissingMeasuresCheckFactory.create(workbasket=workbasket)
    create_missing_measure_comm_codes(
        pref.transaction.pk,
        [new_commodity.pk],
        10,
        missing_measures_check,
    )
    failed_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
        successful=False,
    )
    assert not failed_comm_codes
