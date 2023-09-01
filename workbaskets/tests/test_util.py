import pytest

from common.tests import factories
from workbaskets.util import TableRow
from workbaskets.util import find_comm_code
from workbaskets.util import find_date
from workbaskets.util import get_delimiter


@pytest.mark.parametrize(
    "date_string,exp",
    [
        ("30-12-2020", "-"),
        ("30/12/2020", "/"),
        ("30+12+2020", None),
    ],
)
def test_get_date_delimiter(date_string, exp):
    delimiter = get_delimiter(date_string)
    assert delimiter == exp


@pytest.mark.django_db
def test_get_comm_code():
    created_commodity = factories.GoodsNomenclatureFactory()
    row_data = TableRow()
    find_comm_code(created_commodity.item_id, row_data)
    assert row_data.commodity == created_commodity


@pytest.mark.parametrize(
    "cell,exp",
    [
        ("12-05-2020", "12-05-2020"),
        ("12230984", None),
        ("04-04", None),
        ("-----", None),
    ],
)
def test_find_dates(cell, exp):
    found_date = find_date(cell)
    assert found_date == exp
