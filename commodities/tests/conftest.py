import pytest

from common.tests import factories


@pytest.fixture
def normal_good(date_ranges):
    return factories.GoodsNomenclatureFactory(valid_between=date_ranges.normal)
