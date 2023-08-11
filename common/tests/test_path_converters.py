from datetime import date

import pytest

from common.path_converters import TaricDateRangeConverter
from common.util import TaricDateRange


@pytest.mark.parametrize(
    "date_object,url",
    [
        (TaricDateRange(date(2020, 1, 1), date(2050, 2, 2)), "2020-01-01--2050-02-02"),
        (TaricDateRange(date(2020, 11, 11), None), "2020-11-11--"),
    ],
)
def test_taric_date_range_converter(date_object, url):
    converter = TaricDateRangeConverter()
    output = converter.to_url(date_object)
    assert output == url
