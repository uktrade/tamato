from datetime import date
from datetime import timedelta
from tempfile import NamedTemporaryFile

import pytest

from common.tests import factories
from common.util import TaricDateRange
from exporter.quotas_sqlite.runner import QuotaSqliteExport
from exporter.quotas_sqlite import utils


pytestmark = pytest.mark.django_db


@pytest.mark.exporter
class TestUtils:
    def test_get_monetary_unit_populated(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=factories.MonetaryUnitFactory(),
            measurement_unit=None,
        )

        assert (
            utils.get_monetary_unit(quota)
            == f"{quota.monetary_unit.description} ({quota.monetary_unit.code})"
        )

    def test_get_monetary_unit_blank(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=None,
            measurement_unit=factories.MeasurementUnitFactory(),
        )

        assert utils.get_monetary_unit(quota) is None

    def test_get_measurement_unit_blank(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=factories.MonetaryUnitFactory(),
            measurement_unit=None,
        )

        assert utils.get_measurement_unit(quota) is None

    def test_get_measurement_unit_populated(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=None,
            measurement_unit=factories.MeasurementUnitFactory(
                code="AAA",
                description="BBB",
            ),
        )

        assert utils.get_measurement_unit(quota) == "BBB"

    def test_get_measurement_unit_populated_with_abbreviation(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=None,
            measurement_unit=factories.MeasurementUnitFactory(
                code="AAA",
                description="BBB",
                abbreviation="zzz",
            ),
        )

        assert utils.get_measurement_unit(quota) == "BBB (zzz)"

    def test_get_api_query_date(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=365),
            ),
        )

        assert utils.get_api_query_date(quota) == date.today() + timedelta(days=+365)

    def test_get_api_query_measures_included(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
        )

        factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
        )

        factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=365),
            ),
        )

        assert utils.get_api_query_date(quota) == date.today()

    def test_get_associated_measures(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=10),
            ),
        )

        measure_included_1 = factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
        )

        measure_excluded_1 = factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=20),
                date.today() + timedelta(days=365),
            ),
        )

        measures = utils.get_associated_measures(quota)
        assert measure_included_1 in measures
        assert measure_excluded_1 not in measures

    def test_get_goods_nomenclature_item_ids(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=10),
            ),
        )

        measure_included_1 = factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
        )

        measure_excluded_1 = factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=20),
                date.today() + timedelta(days=365),
            ),
        )

        item_ids = utils.get_goods_nomenclature_item_ids(quota)
        assert measure_included_1.goods_nomenclature.item_id in item_ids
        assert measure_excluded_1.goods_nomenclature.item_id not in item_ids

    def test_get_goods_nomenclature_headings(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=10),
            ),
        )

        factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
            goods_nomenclature__description__description="gggg",
            goods_nomenclature__item_id="0102030405",
        )

        factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
            goods_nomenclature__description__description="hhhh",
            goods_nomenclature__item_id="0102778899",
        )

        factories.GoodsNomenclatureFactory(
            item_id="0102000000",
            description__description="zzz",
        )

        item_ids = utils.get_goods_nomenclature_item_ids(quota)
        headings = utils.get_goods_nomenclature_headings(item_ids)
        assert headings == ["0102 - zzz"]

