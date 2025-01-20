from datetime import date
from datetime import timedelta
from tempfile import NamedTemporaryFile

import pytest

from common.tests import factories
from common.util import TaricDateRange
from exporter.quotas.runner import QuotaExport

pytestmark = pytest.mark.django_db


@pytest.mark.exporter
class TestQuotaExport:
    target_class = QuotaExport

    def get_target(self):
        ntf = NamedTemporaryFile()
        return self.target_class(ntf)

    def test_init(self):
        ntf = NamedTemporaryFile()
        target = self.target_class(ntf)
        assert target.target_file == ntf

    def test_csv_headers(self):
        target = self.get_target()
        assert len(target.csv_headers()) == 13

    def test_get_geographical_areas_and_exclusions(self):
        # seed setup
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
        )
        exclusion = factories.QuotaOrderNumberOriginExclusionFactory(
            origin=quota.order_number.quotaordernumberorigin_set.first(),
        )

        target = self.get_target()
        geo_areas, geo_area_exclusions = target.get_geographical_areas_and_exclusions(
            quota,
        )
        for origin in quota.order_number.quotaordernumberorigin_set.all():
            assert (
                origin.geographical_area.descriptions.all().last().description
                in geo_areas
            )
        assert (
            exclusion.excluded_geographical_area.descriptions.all().last().description
            in geo_area_exclusions
        )

    def test_get_monetary_unit_populated(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=factories.MonetaryUnitFactory(),
            measurement_unit=None,
        )

        target = self.get_target()
        assert (
            target.get_monetary_unit(quota)
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

        target = self.get_target()
        assert target.get_monetary_unit(quota) is None

    def test_get_measurement_unit_blank(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=+365),
            ),
            monetary_unit=factories.MonetaryUnitFactory(),
            measurement_unit=None,
        )

        target = self.get_target()
        assert target.get_measurement_unit(quota) is None

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

        target = self.get_target()
        assert target.get_measurement_unit(quota) == "BBB"

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

        target = self.get_target()
        assert target.get_measurement_unit(quota) == "BBB (zzz)"

    def test_get_api_query_date(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=365),
            ),
        )

        target = self.get_target()
        assert target.get_api_query_date(quota) == date.today() + timedelta(days=+365)

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

        target = self.get_target()
        assert target.get_api_query_date(quota) == date.today()

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

        target = self.get_target()
        measures = target.get_associated_measures(quota)
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

        target = self.get_target()
        item_ids = target.get_goods_nomenclature_item_ids(quota)
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

        target = self.get_target()
        item_ids = target.get_goods_nomenclature_item_ids(quota)
        headings = target.get_goods_nomenclature_headings(item_ids)
        assert headings == "0102-zzz"

    def test_run(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=10),
            ),
            sid=20001,
            order_number__order_number="056789",
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

        with NamedTemporaryFile() as ntf:
            target = self.target_class(ntf)
            target.run()
            content = open(ntf.name, "r").read()

        headers_str = (
            "quota_definition__sid,quota__order_number,"
            + "quota__geographical_areas,"
            + "quota__geographical_area_exclusions,"
            + "quota__headings,"
            + "quota__commodities,"
            + "quota__measurement_unit,"
            + "quota__monetary_unit,"
            + "quota_definition__description,"
            + "quota_definition__validity_start_date,"
            + "quota_definition__validity_end_date,"
            + "quota_definition__initial_volume,"
            + "api_query_date"
        )

        assert headers_str in content
        # check rows count
        assert len(content.split("\n")) > 2
        assert "0102-zzz" in content
        assert "20001,056789" in content
