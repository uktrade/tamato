from datetime import datetime
from datetime import timedelta
from typing import cast
from typing import Dict
from typing import Iterator
from typing import List

import pytz
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.management.commands.utils import blank
from measures.models import Measure
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket

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


class MeasureEndingPattern:
    """A pattern used for end-dating measures. This pattern will accept an old
    measure and will decide whether it needs to be end-dated (it starts before the
    specified date) or deleted (it starts after the specified date)."""

    def __init__(
        self,
        workbasket: WorkBasket,
        measure_types: Dict[int, MeasureType] = {},
        geo_areas: Dict[int, GeographicalArea] = {},
    ) -> None:
        self.workbasket = workbasket
        self.measure_types = measure_types
        self.geo_areas = geo_areas

    def end_date_measure(
        self,
        old_row: OldMeasureRow,
        terminating_regulation: Regulation,
        new_start_date: datetime = BREXIT,
    ) -> Iterator[TrackedModel]:
        if not old_row.inherited_measure:
            # Make sure we have loaded the types and areas we need
            if old_row.measure_type not in self.measure_types:
                self.measure_types[old_row.measure_type] = MeasureType.objects.get(
                    sid=old_row.measure_type
                )
            if old_row.geo_sid not in self.geo_areas:
                self.geo_areas[old_row.geo_sid] = GeographicalArea.objects.get(
                    sid=old_row.geo_sid
                )

            # If the old measure starts after Brexit, we instead
            # need to delete it and it will never come into force
            # If it ends before Brexit, we don't need to do anything!
            starts_after_brexit = old_row.measure_start_date >= new_start_date
            ends_before_brexit = (
                old_row.measure_end_date and old_row.measure_end_date < new_start_date
            )

            generating_regulation = Regulation.objects.get(
                role_type=old_row.regulation_role,
                regulation_id=old_row.regulation_id,
            )

            if old_row.justification_regulation_id and starts_after_brexit:
                # We are going to delete the measure, but we still need the
                # regulation to be correct if it has already been end-dated
                assert old_row.measure_end_date
                justification_regulation = Regulation.objects.get(
                    role_type=old_row.regulation_role,
                    regulation_id=old_row.regulation_id,
                )
            elif not starts_after_brexit:
                # We are going to end-date the measure, and terminate it with
                # the UKGT SI.
                justification_regulation = terminating_regulation
            else:
                # We are going to delete the measure but it has not been end-dated.
                assert old_row.measure_end_date is None
                justification_regulation = None

            if not ends_before_brexit:
                yield Measure(
                    sid=old_row.measure_sid,
                    measure_type=self.measure_types[old_row.measure_type],
                    geographical_area=self.geo_areas[old_row.geo_sid],
                    goods_nomenclature=old_row.goods_nomenclature,
                    additional_code=(
                        AdditionalCode.objects.get(sid=old_row.additional_code_sid)
                        if old_row.additional_code_sid
                        else None
                    ),
                    valid_between=DateTimeTZRange(
                        old_row.measure_start_date,
                        (
                            old_row.measure_end_date
                            if starts_after_brexit
                            else new_start_date - timedelta(days=1)
                        ),
                    ),
                    generating_regulation=generating_regulation,
                    terminating_regulation=justification_regulation,
                    stopped=old_row.stopped,
                    reduction=old_row.reduction,
                    export_refund_nomenclature_sid=old_row.export_refund_sid,
                    update_type=(
                        UpdateType.DELETE if starts_after_brexit else UpdateType.UPDATE
                    ),
                    workbasket=self.workbasket,
                )
