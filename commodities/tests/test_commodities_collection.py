import pytest

from commodities.models.dc import Commodity
from commodities.models.dc import CommodityChange
from commodities.models.dc import CommodityCollection
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


class TestCommodityCollection:
    def test_init(self):
        target = CommodityCollection([])
        assert len(target.commodities) == 0

    def test_init_valid_arguments(self):
        parent_good = factories.GoodsNomenclatureFactory.create(
            item_id="2903691100",
            suffix=10,
            indent__indent=2,
        )

        child_good_1 = factories.GoodsNomenclatureFactory.create(
            item_id="2903691100",
            suffix=80,
            indent__indent=3,
        )

        child_good_2 = factories.GoodsNomenclatureFactory.create(
            item_id="2903691900",
            suffix=80,
            indent__indent=3,
        )

        target = CommodityCollection([parent_good, child_good_1, child_good_2])
        assert len(target.commodities) == 3

    def test_init_invalid_arguments(self):
        # with pytest.raises()
        target = CommodityCollection(["a", "b"])
        assert len(target.commodities) == 2

    def test_update_delete(self):
        change_sequence = []
        # for delete, only current is required
        current = factories.GoodsNomenclatureFactory.create(
            item_id="2903691100",
            suffix=10,
            indent__indent=2,
        )

        target = CommodityCollection([Commodity(current)])
        change_sequence.append(
            CommodityChange(
                collection=target,
                update_type=UpdateType.DELETE,
                current=Commodity(current),
            ),
        )
        target.update(change_sequence)
