import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_goods_nomenclature_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.GoodsNomenclatureFactory,
        "in_use",
        factories.MeasureFactory,
        "goods_nomenclature",
    )
