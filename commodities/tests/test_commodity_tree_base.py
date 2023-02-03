import pytest

from commodities.models.dc import CommodityTreeBase

pytestmark = pytest.mark.django_db


class TestCommodityTreeBase:
    def test_init(self):
        target = CommodityTreeBase([])
        assert len(target.commodities) == 0
