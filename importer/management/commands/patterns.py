from datetime import datetime
from datetime import timedelta
from typing import List

import pytz
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature

# The timezone of GB.
LONDON = pytz.timezone("Europe/London")

# The date of the end of the transition period,
# localized to the Europe/London timezone.
BREXIT = LONDON.localize(datetime(2021, 1, 1))


class OldMeasureRow:
    def __init__(self, old_row: List[Cell]) -> None:
        assert old_row is not None
        self.goods_nomenclature_sid = int(old_row[0].value)
        self.item_id = str(old_row[1].value)
        self.inherited_measure = bool(old_row[6].value)
        self.measure_sid = int(old_row[7].value)
        self.measure_type = int(old_row[8].value)
        self.geo_sid = int(old_row[13].value)
        self.measure_start_date = self.parse_date(old_row[16].value)
        self.measure_end_date = blank(old_row[17].value, self.parse_date)
        self.regulation_role = int(old_row[18].value)
        self.regulation_id = str(old_row[19].value)
        self.order_number = blank(old_row[15].value, int)
        self.justification_regulation_role = blank(old_row[20].value, int)
        self.justification_regulation_id = blank(old_row[21].value, str)
        self.stopped = bool(old_row[24].value)
        self.additional_code_sid = blank(old_row[23].value, int)
        self.export_refund_sid = blank(old_row[25].value, int)
        self.reduction = blank(old_row[26].value, int)
        self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
            sid=self.goods_nomenclature_sid
        )

    def parse_date(self, value: str) -> datetime:
        return LONDON.localize(datetime.strptime(value, r"%Y-%m-%d"))
