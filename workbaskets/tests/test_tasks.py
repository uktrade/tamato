from unittest.mock import patch

import pytest

from checks.models import MissingMeasureCommCode
from checks.tests.factories import MissingMeasuresCheckFactory
from common.models import Transaction
from common.tests import factories
from workbaskets.tasks import check_workbasket_for_missing_measures
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


@patch("workbaskets.tasks.get_comm_codes_with_missing_measures")
def test_check_workbasket_for_missing_measures(mock_check_comm_codes):
    workbasket = factories.WorkBasketFactory.create()
    commodity1 = factories.GoodsNomenclatureFactory.create()
    commodity2 = factories.GoodsNomenclatureFactory.create()
    mock_check_comm_codes.return_value = [commodity1, commodity2]
    comm_code_pks = [commodity1.pk, commodity2.pk]

    check_workbasket_for_missing_measures(
        workbasket_id=workbasket.id,
        tx_pk=commodity2.transaction.pk,
        comm_code_pks=comm_code_pks,
    )
    assert workbasket.missing_measures_check is not None
    assert workbasket.missing_measures_check.successful == False

    missing_measure_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
    )

    assert {item.commodity.pk for item in missing_measure_comm_codes} == set(
        comm_code_pks,
    )


@patch("workbaskets.tasks.get_comm_codes_with_missing_measures")
def test_check_workbasket_for_missing_measures_existing_check_success(
    mock_check_comm_codes,
):
    workbasket = factories.WorkBasketFactory.create()
    commodity1 = factories.GoodsNomenclatureFactory.create()
    commodity2 = factories.GoodsNomenclatureFactory.create()
    mock_check_comm_codes.return_value = []
    comm_code_pks = [commodity1.pk, commodity2.pk]

    MissingMeasuresCheckFactory.create(workbasket=workbasket)

    check_workbasket_for_missing_measures(
        workbasket_id=workbasket.id,
        tx_pk=commodity2.transaction.pk,
        comm_code_pks=comm_code_pks,
    )
    assert workbasket.missing_measures_check is not None
    assert workbasket.missing_measures_check.successful == True

    missing_measure_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
    )

    assert missing_measure_comm_codes.count() == 0


@patch("workbaskets.tasks.get_comm_codes_with_missing_measures")
def test_check_workbasket_for_missing_measures_success(mock_check_comm_codes):
    workbasket = factories.WorkBasketFactory.create()
    commodity1 = factories.GoodsNomenclatureFactory.create()
    commodity2 = factories.GoodsNomenclatureFactory.create()
    mock_check_comm_codes.return_value = []
    comm_code_pks = [commodity1.pk, commodity2.pk]

    check_workbasket_for_missing_measures(
        workbasket_id=workbasket.id,
        tx_pk=commodity2.transaction.pk,
        comm_code_pks=comm_code_pks,
    )
    assert workbasket.missing_measures_check is not None
    assert workbasket.missing_measures_check.successful == True

    missing_measure_comm_codes = MissingMeasureCommCode.objects.filter(
        missing_measures_check__workbasket=workbasket,
    )

    assert missing_measure_comm_codes.count() == 0
