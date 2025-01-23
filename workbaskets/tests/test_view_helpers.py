import pytest

from commodities.models.orm import GoodsNomenclature
from common.tests import factories
from workbaskets.views.helpers import get_comm_codes_affected_by_workbasket_changes

pytestmark = pytest.mark.django_db


def test_get_goods_nom():
    workbasket = factories.WorkBasketFactory.create()

    with workbasket.new_transaction():
        factories.GoodsNomenclatureFactory.create()
        factories.GoodsNomenclatureFactory.create()

    result = get_comm_codes_affected_by_workbasket_changes(workbasket)
    assert result
    # each GoodsNomenclatureFactory creates an origin as well so there will be 4 total
    assert len(result) == 4
    comm_codes = GoodsNomenclature.objects.filter(pk__in=result)
    assert set([item.__class__._meta.verbose_name for item in comm_codes]) == {
        "commodity code",
    }
