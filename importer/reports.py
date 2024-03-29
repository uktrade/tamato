from __future__ import annotations

import csv
import logging
from collections import OrderedDict
from contextlib import closing
from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import Optional
from typing import Tuple
from typing import Union

import requests

from commodities.models.code import CommodityCode
from commodities.models.orm import GoodsNomenclature
from common.validators import UpdateType
from measures.models import Measure
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

API_PROTOCOL = "https"
API_HOST = "data.api.trade.gov.uk"
API_PATH_DATASETS = "v1/datasets/uk-tariff-2021-01-01/versions/latest/tables/"
API_ENDPOINT_DEF = "measures-as-defined"
API_ENDPOINT_DECL = "measures-on-declarable-commodities"

URL_PREFIX = f"{API_PROTOCOL}://{API_HOST}/{API_PATH_DATASETS}"
URL_SUFFIX = "/data?format=csv&download"

URL_DEF = f"{URL_PREFIX}{API_ENDPOINT_DEF}{URL_SUFFIX}"
URL_DECL = f"{URL_PREFIX}{API_ENDPOINT_DECL}{URL_SUFFIX}"

CMT_ADDITIONAL_CODE = "Additional Code"
CMT_COMMODITY_CODE = "Commodity Code"
CMT_CONDITIONS = "Conditions"
CMT_DUTY_EXPRRESSION = "Duty Expression"
CMT_EXCLUDED_ORIGINS = "Excluded Origins"
CMT_FOOTNOTES = "Footnotes"
CMT_MEASURE_END_DATE = "End Date"
CMT_MEASURE_SID = "SID"
CMT_MEASURE_START_DATE = "Start Date"
CMT_MEASURE_TYPE_DESCRIPTION = "Measure Type Description"
CMT_ORIGIN = "Origin"
CMT_QUOTA_ORDER_NUMBER = "Quota Order Number"
CMT_REGULATION_ID = "Regulation ID"

CMT_HEADERS = (
    CMT_COMMODITY_CODE,
    CMT_MEASURE_TYPE_DESCRIPTION,
    CMT_DUTY_EXPRRESSION,
    CMT_ORIGIN,
    CMT_EXCLUDED_ORIGINS,
    CMT_QUOTA_ORDER_NUMBER,
    CMT_MEASURE_START_DATE,
    CMT_MEASURE_END_DATE,
    CMT_REGULATION_ID,
    CMT_ADDITIONAL_CODE,
    CMT_FOOTNOTES,
    CMT_CONDITIONS,
    CMT_MEASURE_SID,
)

MAD_ADDITIONAL_CODE = "measure__additional_code__code"
MAD_COMMODITY_CODE = "commodity__code"
MAD_CONDITIONS = "measure__conditions"
MAD_DUTY_EXPRESSION = "measure__duty_expression"
MAD_EXCLUDED_GEO_AREA_DESCRIPTIONS = (
    "measure__excluded_geographical_areas__descriptions"
)
MAD_FOOTNOTES = "measure__footnotes"
MAD_GEO_AREA_DESCRIPTION = "measure__geographical_area__description"
MAD_MEASURE_END_DATE = "measure__effective_end_date"
MAD_MEASURE_SID = "measure__sid"
MAD_MEASURE_START_DATE = "measure__effective_start_date"
MAD_MEASURE_TYPE_DESCRIPTION = "measure__type__description"
MAD_QUOTA_ORDER_NUMBER = "measure__quota__order_number"
MAD_REGULATION_ID = "measure__regulation__id"

MAPPING_MAD_CMT = (
    (MAD_COMMODITY_CODE, CMT_COMMODITY_CODE),
    (MAD_MEASURE_TYPE_DESCRIPTION, CMT_MEASURE_TYPE_DESCRIPTION),
    (MAD_DUTY_EXPRESSION, CMT_DUTY_EXPRRESSION),
    (MAD_GEO_AREA_DESCRIPTION, CMT_ORIGIN),
    (MAD_EXCLUDED_GEO_AREA_DESCRIPTIONS, CMT_EXCLUDED_ORIGINS),
    (MAD_QUOTA_ORDER_NUMBER, CMT_QUOTA_ORDER_NUMBER),
    (MAD_MEASURE_START_DATE, CMT_MEASURE_START_DATE),
    (MAD_MEASURE_END_DATE, CMT_MEASURE_END_DATE),
    (MAD_REGULATION_ID, CMT_REGULATION_ID),
    (MAD_ADDITIONAL_CODE, CMT_ADDITIONAL_CODE),
    (MAD_FOOTNOTES, CMT_FOOTNOTES),
    (MAD_CONDITIONS, CMT_CONDITIONS),
    (MAD_MEASURE_SID, CMT_MEASURE_SID),
)


TMadItemGenerator = Generator[None, Dict[str, Any], None]
TMadItemCollection = Tuple[Dict[str, Any]]
TGoods = Tuple[GoodsNomenclature]

# Acronyms:
# MaD - measures-as-defined template
# CM - create measures template


def sanitized_mad_value(value: Union[str, int, float]) -> Union[str, int, float]:
    """Returns a sanitized version of a single value from MaD."""
    if not isinstance(value, str):
        return value
    return value.replace("#NA", "")


def get_filtered_mad_items(
    key: str,
    values: Iterable[str],
    as_defined: Optional[bool] = True,
) -> TMadItemGenerator:
    """
    Returns filtered MaD data, re-arranged in create-measures template format.

    The function arguments are:
    - key: the column name to look up in each row
    - values: the values list that filtered rows must match in the key column
    - as_defined: if True, use the measures-as-defined template,
        else use the measures-as-declared template.
    """
    url = URL_DEF if as_defined else URL_DECL

    with closing(requests.get(url, stream=True)) as r:
        f = (line.decode("utf-8") for line in r.iter_lines())
        reader = csv.DictReader(f, delimiter=",", quotechar='"')
        filtered_reader = filter(lambda x: x[key] in values, reader)

        for item in filtered_reader:
            regulation = (
                Measure.objects.filter(
                    sid=item[MAD_MEASURE_SID],
                )
                .order_by("id")
                .last()
                .generating_regulation
            )

            item[MAD_REGULATION_ID] = str(regulation)

            mapped_item = OrderedDict(
                (mapped_key, sanitized_mad_value(item[key]))
                for key, mapped_key in MAPPING_MAD_CMT
            )

            yield mapped_item


def get_goods_mad_items(
    goods: Iterable[GoodsNomenclature],
    as_defined: Optional[bool] = True,
) -> TMadItemGenerator:
    """Returns create-measures template rows that match a set of commodity
    codes."""
    key = MAD_COMMODITY_CODE
    codes = [good.item_id for good in goods]
    return get_filtered_mad_items(key, codes, as_defined=as_defined)


def get_measures_mad_items(
    measures: Iterable[Measure],
    as_defined: Optional[bool] = True,
) -> TMadItemGenerator:
    """Returns create-measures template rows that match a set of measure
    sid-s."""
    key = MAD_MEASURE_SID
    sids = [str(measure.sid) for measure in measures]
    return get_filtered_mad_items(key, sids, as_defined=as_defined)


class MeasureChangeReports:
    """Provides a generator changed measure reports."""

    def __init__(self, workbasket: WorkBasket) -> None:
        self.workbasket = workbasket
        self.transactions = workbasket.transactions.all()

    def report_affected_measures(
        self,
        as_defined: Optional[bool] = True,
    ) -> TMadItemCollection:
        """
        Returns affected measures from a commodity import in create-measures
        template layout.

        Note: This method also persists the report locally.
        """
        data = tuple(
            get_measures_mad_items(
                self.affected_measures,
                as_defined,
            ),
        )

        if not data:
            logger.info("There were no affected measures")
            return

        measures = {m.sid: m for m in self.affected_measures}
        for item in data:
            sid = int(item[CMT_MEASURE_SID])
            measure = measures[sid]
            item["Change summary"] = UpdateType(measure.update_type).name.lower()

            item_id = item[CMT_COMMODITY_CODE]
            code = CommodityCode(code=item_id)
            item["Measure level"] = len(code.trimmed_code)

        return data

    def report_related_measures(self) -> TMadItemCollection:
        """
        Returns related measures from a commodity import in create-measures
        template layout.

        Not all measures related to the imported commodities are also affected
        by the side effects of the import.
        """

        goods = self.updated_goods + self.deleted_goods
        return tuple(get_goods_mad_items(goods))

    @property
    def affected_measures(self) -> Tuple[Measure]:
        """
        Returns all affected measures in the import.

        NOTE: This method presumes that the imported envelope
        was filtered to only process commodity changes.
        Therefore, any changes to measures in this workbasket
        would be the result of preemptive actions
        taken by the commodity change handler.
        """

        return tuple(
            [
                record
                for transaction in self.transactions
                for record in transaction.tracked_models.all()
                if type(record) == Measure
            ],
        )

    @property
    def goods(self) -> Tuple[GoodsNomenclature]:
        """Returns all goods_nomenclature records in the workbasket."""
        return tuple(
            [
                record
                for transaction in self.transactions
                for record in transaction.tracked_models.all()
                if type(record) == GoodsNomenclature
            ],
        )

    @property
    def created_goods(self) -> Tuple[GoodsNomenclature]:
        """Returns created goods_nomenclature records in the workbasket."""
        return self._get_goods_by_update_type(UpdateType.CREATE)

    @property
    def deleted_goods(self) -> Tuple[GoodsNomenclature]:
        """Returns deleted goods_nomenclature records in the workbasket."""
        return self._get_goods_by_update_type(UpdateType.DELETE)

    @property
    def updated_goods(self) -> Tuple[GoodsNomenclature]:
        """Returns updated goods_nomenclature records in the workbasket."""
        return self._get_goods_by_update_type(UpdateType.UPDATE)

    def _get_goods_by_update_type(
        self,
        update_type: UpdateType,
    ) -> Tuple[GoodsNomenclature]:
        """Returns goods records in the workbasket with the update type."""
        return tuple(
            sorted(
                [record for record in self.goods if record.update_type == update_type],
                key=lambda x: x.transaction.order,
            ),
        )
