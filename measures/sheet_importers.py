import logging
from datetime import date
from datetime import datetime
from functools import cached_property
from functools import reduce
from typing import Optional
from typing import Sequence

import parsec
from django.core.exceptions import MultipleObjectsReturned
from django.db.models.query_utils import Q

from additional_codes.models import AdditionalCode
from commodities.models import GoodsNomenclature
from commodities.util import clean_item_id
from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from importer.sheet import CellValue
from importer.sheet import SheetRowMixin
from importer.sheet import column
from measures.models import Measure
from measures.models import MeasureType
from measures.patterns import MeasureCreationPattern
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


def process_date_value(value: CellValue) -> date:
    """
    Returns a date instance corresponding to the cell value.

    The date part of the value must be in "%Y-%m-%d" format. If a value
    representing date and time is provided, this method will take the date part
    only.
    """
    value = str(value).split(" ", 1)[0]
    return datetime.strptime(value, r"%Y-%m-%d").date()


class MeasureSheetRow(SheetRowMixin):
    """An importer that will parse values from a human-readable spreadsheet of
    measures and will create one measure for each row that it finds."""

    @column("A")
    def item_id(self, value: CellValue) -> str:
        return clean_item_id(value)

    @cached_property
    def goods_nomenclature(self) -> GoodsNomenclature:
        return (
            GoodsNomenclature.objects.latest_approved()
            .as_at(self.validity_start_date)
            .get(item_id=self.item_id, suffix="80")
        )

    @column("B")
    def measure_type_description(self, value: CellValue) -> str:
        return str(value)

    @cached_property
    def measure_type(self) -> MeasureType:
        qs = MeasureType.objects.latest_approved().as_at(self.validity_start_date)

        desc = self.measure_type_description.lower().strip()
        if desc == "export control":
            return qs.get(sid=766)
        elif desc == "import control":
            return qs.get(sid=760)
        elif desc == "restriction on entry into free circulation":
            return qs.get(sid=475)
        elif desc == "restriction on export":
            return qs.get(sid=476)

        return qs.get(description=self.measure_type_description)

    @column("C")
    def duty_sentence(self, value: CellValue) -> str:
        return str(value) if value else ""

    @column("D")
    def origin_description(self, value: CellValue) -> str:
        return str(value)

    @cached_property
    def origin(self) -> GeographicalArea:
        qs = (
            GeographicalAreaDescription.objects.latest_approved()
            .with_end_date()
            .as_at(self.validity_start_date)
        )

        if self.origin_description == "Myanmar (Burma)":
            geo_area = qs.get(sid=1393)
        elif self.origin_description == "European Union":
            geo_area = qs.get(sid=1427)
        else:
            try:
                geo_area = qs.get(description=self.origin_description)
            except GeographicalAreaDescription.DoesNotExist:
                print(self.origin_description)
                raise
            except MultipleObjectsReturned:
                print(self.origin_description)
                raise

        return geo_area.described_geographicalarea

    @column("E", many=True)
    def excluded_origin_descriptions(self, value: CellValue) -> str:
        return str(value)

    @cached_property
    def excluded_origins(self) -> Sequence[GeographicalArea]:
        return [
            desc.described_geographicalarea
            for desc in GeographicalAreaDescription.objects.latest_approved()
            .with_end_date()
            .as_at(self.validity_start_date)
            .filter(description__in=self.excluded_origin_descriptions)
        ]

    @column("F", optional=True)
    def quota_order_number(self, value: CellValue) -> str:
        return str(value)

    @cached_property
    def quota(self) -> Optional[QuotaOrderNumber]:
        try:
            return (
                QuotaOrderNumber.objects.latest_approved()
                .as_at(self.validity_start_date)
                .get(order_number=self.quota_order_number)
                if self.quota_order_number
                else None
            )
        except QuotaOrderNumber.DoesNotExist:
            return None

    @cached_property
    def dead_order_number(self) -> Optional[str]:
        if self.quota_order_number and not self.quota:
            return self.quota_order_number

    @column("G")
    def validity_start_date(self, value: CellValue) -> date:
        return process_date_value(value)

    @column("H", optional=True)
    def validity_end_date(self, value: CellValue) -> date:
        return process_date_value(value)

    @column("I")
    def regulation_id(self, value: CellValue) -> str:
        return str(value)

    @cached_property
    def regulation(self) -> Regulation:
        try:
            return (
                Regulation.objects.latest_approved()
                .as_at(self.validity_start_date)
                .get(regulation_id=self.regulation_id)
            )
        except Regulation.DoesNotExist:
            return

    @column("J", optional=True)
    def additional_code_id(self, value: CellValue) -> str:
        return str(value)

    @cached_property
    def additional_code(self) -> Optional[AdditionalCode]:
        try:
            return (
                (
                    AdditionalCode.objects.latest_approved()
                    .as_at(self.validity_start_date)
                    .get(
                        code=self.additional_code_id[1:],
                        type__sid=self.additional_code_id[0],
                    )
                )
                if self.additional_code_id
                else None
            )
        except AdditionalCode.DoesNotExist:
            return None

    @cached_property
    def dead_additional_code(self) -> Optional[str]:
        if self.additional_code_id and not self.additional_code:
            return str(self.additional_code_id)

    @column("K", many=True)
    def footnote_ids(self, value: CellValue):
        return str(value)

    @cached_property
    def footnotes(self) -> Sequence[Footnote]:
        qs = [
            Q(
                described_footnote__footnote_id=f[2:],
                described_footnote__footnote_type__footnote_type_id=f[:2],
            )
            for f in self.footnote_ids
        ]
        if not qs:
            return []
        q = reduce(lambda x, y: x | y, qs)
        return [
            desc.described_footnote
            for desc in FootnoteDescription.objects.latest_approved()
            .with_end_date()
            .as_at(self.validity_start_date)
            .filter(q)
        ]

    @column("L", optional=True)
    def conditions(self, value: CellValue):
        return str(value)

    def import_row(self, workbasket: WorkBasket) -> Measure:
        if not self.regulation:
            return

        creator = MeasureCreationPattern(
            workbasket=workbasket,
            base_date=self.validity_start_date,
        )

        try:
            kwargs = dict(
                duty_sentence=self.duty_sentence,
                measure_type=self.measure_type,
                goods_nomenclature=self.goods_nomenclature,
                validity_start=self.validity_start_date,
                validity_end=self.validity_end_date,
                geographical_area=self.origin,
                exclusions=self.excluded_origins,
                generating_regulation=self.regulation,
                order_number=self.quota,
                dead_order_number=self.dead_order_number,
                additional_code=self.additional_code,
                dead_additional_code=self.dead_additional_code,
                footnotes=self.footnotes,
                condition_sentence=self.conditions,
            )
            return creator.create(**kwargs)
        except GoodsNomenclature.DoesNotExist:
            logger.warning(
                f"Commodity {self.item_id}: not imported from EU Taric files yet.",
            )
        except parsec.ParseError:
            logger.warning(kwargs)
            raise
