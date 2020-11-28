import logging
from enum import Enum
from functools import cached_property
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from xlrd.sheet import Cell

from certificates.models import Certificate
from common.models import TrackedModel
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import parse_date
from importer.management.commands.patterns import parse_list
from importer.management.commands.patterns import QuotaCreatingPattern
from importer.management.commands.utils import blank
from importer.management.commands.utils import col
from measures.models import Measurement
from quotas.validators import AdministrationMechanism
from quotas.validators import QuotaCategory

logger = logging.getLogger(__name__)


class QuotaType(Enum):
    CALENDAR = "Calendar year"
    NON_CALENDAR = "Non-calendar year"
    SEASONAL = "Seasonal"


class QuotaSource(Enum):
    PREFERENTIAL = "Pref"
    ORIGIN = "Origin"
    WTO = "WTO"


class QuotaRow:
    def __init__(self, row: List[Cell], origin: GeographicalArea) -> None:
        self.origin = origin
        self.origin_ids = parse_list(str(row[col("B")].value))
        if origin.area_id not in self.origin_ids:
            return
        self.excluded_origin_ids = parse_list(str(row[col("C")].value))
        self.order_number = str(row[col("A")].value).strip()
        self.period_start = parse_date(row[col("D")])
        self.period_end = parse_date(row[col("E")])
        self.type = QuotaType(row[col("F")].value)
        self.volume = self.parse_volume(row[col("G")])
        self.interim_volume = blank(row[col("H")], self.parse_volume)
        self.unit = row[col("I")].value  # TODO convert to measurement
        self.qualifier = blank(row[col("J")].value, str)  # TODO convert to measurement
        self.parent_order_number = blank(row[col("L")].value, str)
        self.coefficient = blank(row[col("M")].value, str)
        self.source = QuotaSource(str(row[col("N")].value))
        self.suspension_start = blank(row[col("O")], parse_date)
        self.suspension_end = blank(row[col("P")], parse_date)
        self.certificate_str = blank(row[col("R")].value, str)
        self.end_use = bool(row[col("Q")].value)
        self.mechanism = (
            AdministrationMechanism.LICENSED
            if self.order_number.startswith("054")
            else AdministrationMechanism.FCFS
        )

    def parse_volume(self, cell: Cell) -> int:
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            return int(cell.value)
        else:
            return int(cell.value.replace(",", ""))

    @cached_property
    def excluded_origins(self) -> List[GeographicalArea]:
        return [
            GeographicalArea.objects.get(area_id=e) for e in self.excluded_origin_ids
        ]

    @cached_property
    def measurement(self) -> Measurement:
        kwargs = {"measurement_unit__code": self.unit}
        if self.qualifier is None:
            kwargs["measurement_unit_qualifier"] = None
        else:
            kwargs["measurement_unit_qualifier__code"] = self.qualifier

        return Measurement.objects.as_at(BREXIT).get(**kwargs)

    @cached_property
    def certificate(self) -> Optional[Certificate]:
        if self.certificate_str:
            logger.debug("Looking up certificate %s", self.certificate_str)
            return Certificate.objects.get(
                sid=self.certificate_str[1:],
                certificate_type__sid=self.certificate_str[0],
            )
        else:
            return None


class QuotaImporter(RowsImporter):
    def __init__(self, *args, category: QuotaCategory, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.category = category

    def setup(self) -> Iterator[TrackedModel]:
        self.quota_creator = QuotaCreatingPattern(
            order_number_counter=self.counters["quota_order_number_id"],
            order_number_origin_counter=self.counters["quota_order_number_origin_id"],
            definition_counter=self.counters["quota_definition_id"],
            suspension_counter=self.counters["quota_suspension_id"],
            workbasket=self.workbasket,
            start_date=BREXIT,
        )
        self.quotas = {}
        return iter([])

    def compare_rows(self, new_row: Optional[QuotaRow], old_row: None) -> int:
        assert old_row is None
        return 1 if new_row else -1

    def handle_row(
        self, row: Optional[QuotaRow], old_row: None
    ) -> Iterator[Iterable[TrackedModel]]:
        self.quotas[row.order_number] = row

        models = self.quota_creator.create(
            row.order_number,
            row.mechanism,
            row.origin,
            self.category,
            row.period_start,
            row.period_end,
            row.unit,
            row.volume,
            row.interim_volume,
            row.parent_order_number,
            row.coefficient,
            row.excluded_origins,
            row.suspension_start,
            row.suspension_end,
        )
        if row.mechanism != AdministrationMechanism.LICENSED:
            return models
        else:
            return iter([])
