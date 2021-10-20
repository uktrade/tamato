from __future__ import annotations

import csv
from collections import OrderedDict
from contextlib import closing
from typing import Any
from typing import Generator
from typing import Iterable
from typing import Optional

import requests

from commodities.models import GoodsNomenclature
from common.validators import UpdateType
from measures.models import Measure
from workbaskets.models import WorkBasket

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
)


TMadItemGenerator = Generator[None, OrderedDict[str, Any], None]
TGoods = tuple[GoodsNomenclature]


def get_filtered_mad_items(
    key: str,
    values: Iterable[str],
    as_defined: Optional[bool] = True,
) -> TMadItemGenerator:
    url = URL_DEF if as_defined else URL_DECL

    with closing(requests.get(url, stream=True)) as r:
        f = (line.decode("utf-8") for line in r.iter_lines())
        reader = csv.DictReader(f, delimiter=",", quotechar='"')
        filtered_reader = filter(lambda x: x[key] in values, reader)

        for item in filtered_reader:
            regulation = (
                Measure.objects.latest_approved()
                .get(
                    sid=item[MAD_MEASURE_SID],
                )
                .generating_regulation
            )

            item[MAD_REGULATION_ID] = str(regulation)

            mapped_item = OrderedDict(
                (mapped_key, item[key]) for key, mapped_key in MAPPING_MAD_CMT
            )

            yield mapped_item


def get_goods_mad_items(
    goods: Iterable[GoodsNomenclature],
    as_defined: Optional[bool] = True,
) -> TMadItemGenerator:
    key = MAD_COMMODITY_CODE
    codes = [good.item_id for good in goods]
    return get_filtered_mad_items(key, codes, as_defined=as_defined)


def get_measures_mad_items(
    measures: Iterable[Measure],
    as_defined: Optional[bool] = True,
) -> TMadItemGenerator:
    key = MAD_MEASURE_SID
    sids = [str(measure.sid) for measure in measures]
    return get_filtered_mad_items(key, sids, as_defined=as_defined)


class CommodityChangeReports:
    def __init__(self, workbasket: WorkBasket) -> None:
        self.transactions = workbasket.transactions.all()

    def report_affected_measures(
        self,
        as_defined: Optional[bool] = True,
    ) -> TMadItemGenerator:
        return get_measures_mad_items(self.affected_measures)

    def report_related_measures(
        self,
        as_defined: Optional[bool] = True,
    ) -> TMadItemGenerator:
        goods = self.updated_goods + self.deleted_goods
        return get_goods_mad_items(goods)

    @property
    def affected_measures(self) -> tuple[Measure]:
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
                if transaction.order < 0
                for record in transaction.tracked_models.all()
                if type(record) == Measure
            ],
        )

    @property
    def goods(self) -> tuple[GoodsNomenclature]:
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
    def created_goods(self) -> tuple[GoodsNomenclature]:
        """Returns created goods_nomenclature records in the workbasket."""
        return self._get_goods_by_update_type(UpdateType.CREATE)

    @property
    def deleted_goods(self) -> tuple[GoodsNomenclature]:
        """Returns deleted goods_nomenclature records in the workbasket."""
        return self._get_goods_by_update_type(UpdateType.DELETE)

    @property
    def updated_goods(self) -> tuple[GoodsNomenclature]:
        """Returns updated goods_nomenclature records in the workbasket."""
        return self._get_goods_by_update_type(UpdateType.UPDATE)

    def _get_goods_by_update_type(
        self,
        update_type: UpdateType,
    ) -> tuple[GoodsNomenclature]:
        """Returns goods records in the workbasket with the update type."""
        return tuple(
            sorted(
                [record for record in self.goods if record.update_type == update_type],
                key=lambda x: x.transaction.order,
            ),
        )
