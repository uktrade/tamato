from datetime import date
from datetime import timedelta

import pytest

from commodities.helpers import get_measures_on_declarable_commodities
from commodities.models.orm import GoodsNomenclature
from common.tests import factories
from common.util import TaricDateRange

pytestmark = pytest.mark.django_db


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
    assert measure1 in result
    assert measure2 in result
