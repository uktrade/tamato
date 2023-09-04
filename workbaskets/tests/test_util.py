from datetime import date

import pytest

from common.tests import factories
from common.util import TaricDateRange
from workbaskets.util import TableRow
from workbaskets.util import assign_validity
from workbaskets.util import find_comm_code
from workbaskets.util import find_date
from workbaskets.util import get_delimiter
from workbaskets.util import parse_dates
from workbaskets.util import serialize_uploaded_data


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


@pytest.mark.parametrize(
    "dates",
    [
        (["01-01-2020", "01-01-2000"]),
        (["2020-01-01", "2000-01-01"]),
        (["2020-01-01", "01-01-2000"]),
    ],
)
def test_parse_dates(dates):
    assert set(parse_dates(dates)) == {date(2020, 1, 1), date(2000, 1, 1)}


@pytest.mark.parametrize(
    "dates",
    [
        (["01-01-2020", "01-01-2000"]),
        (["01-01-2000", "01-01-2020"]),
    ],
)
def test_assign_validity(dates):
    row_data = TableRow()
    assign_validity(dates, row_data)
    assert row_data.valid_between == TaricDateRange(date(2000, 1, 1), date(2020, 1, 1))


@pytest.mark.django_db
def test_serialize_uploaded_data():
    commodity1 = factories.GoodsNomenclatureFactory()
    commodity2 = factories.GoodsNomenclatureFactory()

    # format of copypasted data from excel
    # each cell is separated by a \t tab character
    # at the moment we only match measures against comm code, duty, and start/end dates
    raw_data = (
        f"{commodity1.item_id}\t0.000% + 2.000 GBP / 100 kg\t20/05/2021\t31/08/2024\n"
        f"{commodity2.item_id}\t0.000%\t\t31/08/2024\n"
        "3945875\tfoo bar\t438573\t\n"  # line with nonsense data
    )
    serialized = serialize_uploaded_data(raw_data)
    assert len(serialized) == 2
    assert serialized[0].valid_between == TaricDateRange(
        date(2021, 5, 20),
        date(2024, 8, 31),
    )
    assert serialized[0].commodity == commodity1
    assert serialized[1].valid_between == TaricDateRange(date(2024, 8, 31), None)
    assert serialized[1].commodity == commodity2
