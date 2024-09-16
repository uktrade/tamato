from datetime import date

import pytest

from common.tests.factories import DutyExpressionFactory
from common.tests.factories import GeographicalAreaFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import MeasureComponentFactory
from common.tests.factories import MeasureFactory
from common.util import TaricDateRange
from reference_documents.check.ref_rates import RateChecks
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories
from reference_documents.tests.factories import RefRateFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRateExists:
    def test_run_check_pass(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        ref_rate = RefRateFactory.create(
            duty_rate="12%",
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        tap_goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_rate.commodity_code,
            valid_between=valid_between,
        )

        tap_measure = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=valid_between,
            goods_nomenclature=tap_goods_nomenclature,
            geographical_area__area_id=area_id,
        )

        tap_duty_expression = DutyExpressionFactory.create(
            duty_amount_applicability_code=1,
            valid_between=TaricDateRange(date(2000, 1, 1)),
            prefix="",
            measurement_unit_applicability_code=0,
            monetary_unit_applicability_code=0,
            description="% or amount",
        )

        tap_measure_component = MeasureComponentFactory.create(
            component_measure=tap_measure,
            duty_amount=12.0,
            duty_expression=tap_duty_expression,
        )

        target = RateChecks(ref_rate=ref_rate)
        assert target.run_check() == (AlignmentReportCheckStatus.PASS, "")

    def test_run_check_fail_no_comm_code(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        ref_rate = RefRateFactory.create(
            duty_rate="12%",
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        target = RateChecks(ref_rate=ref_rate)
        assert target.run_check() == (
            AlignmentReportCheckStatus.FAIL,
            f"{ref_rate.commodity_code} None comm code not live",
        )

    def test_run_check_pass_but_defined_on_child_com_codes(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"
        comm_code = "0102030000"
        comm_code_child_1 = "0102030100"
        comm_code_child_2 = "0102030200"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        ref_rate = RefRateFactory.create(
            duty_rate="12%",
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
            commodity_code="0102030000",
        )

        tap_goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=comm_code,
            valid_between=valid_between,
            indent__indent=1,
        )

        tap_child_goods_nomenclature_1 = GoodsNomenclatureFactory.create(
            item_id=comm_code_child_1,
            valid_between=valid_between,
            indent__indent=2,
        )

        tap_child_goods_nomenclature_2 = GoodsNomenclatureFactory.create(
            item_id=comm_code_child_2,
            valid_between=valid_between,
            indent__indent=2,
        )

        tap_geo_area = GeographicalAreaFactory.create(
            area_id=area_id,
        )

        # Child_1
        tap_measure_child_1 = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=valid_between,
            goods_nomenclature=tap_child_goods_nomenclature_1,
            geographical_area=tap_geo_area,
        )

        tap_duty_expression = DutyExpressionFactory.create(
            duty_amount_applicability_code=1,
            valid_between=TaricDateRange(date(2000, 1, 1)),
            prefix="",
            measurement_unit_applicability_code=0,
            monetary_unit_applicability_code=0,
            description="% or amount",
        )

        tap_measure_component = MeasureComponentFactory.create(
            component_measure=tap_measure_child_1,
            duty_amount=12.0,
            duty_expression=tap_duty_expression,
        )

        # Child_2
        tap_measure_child_1 = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=valid_between,
            goods_nomenclature=tap_child_goods_nomenclature_2,
            geographical_area=tap_geo_area,
        )

        tap_duty_expression = DutyExpressionFactory.create(
            duty_amount_applicability_code=1,
            valid_between=TaricDateRange(date(2000, 1, 1)),
            prefix="",
            measurement_unit_applicability_code=0,
            monetary_unit_applicability_code=0,
            description="% or amount",
        )

        tap_measure_component = MeasureComponentFactory.create(
            component_measure=tap_measure_child_1,
            duty_amount=12.0,
            duty_expression=tap_duty_expression,
        )

        target = RateChecks(ref_rate=ref_rate)
        assert target.run_check() == (
            AlignmentReportCheckStatus.PASS,
            f"{comm_code} : matched with children",
        )

    def test_run_check_fai_partially_defined_on_child_com_code(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"
        comm_code = "0102030000"
        comm_code_child_1 = "0102030100"
        comm_code_child_2 = "0102030200"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        ref_rate = RefRateFactory.create(
            duty_rate="12%",
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
            commodity_code="0102030000",
        )

        tap_goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=comm_code,
            valid_between=valid_between,
            indent__indent=1,
        )

        tap_child_goods_nomenclature_1 = GoodsNomenclatureFactory.create(
            item_id=comm_code_child_1,
            valid_between=valid_between,
            indent__indent=2,
        )

        tap_child_goods_nomenclature_2 = GoodsNomenclatureFactory.create(
            item_id=comm_code_child_2,
            valid_between=valid_between,
            indent__indent=2,
        )

        tap_geo_area = GeographicalAreaFactory.create(
            area_id=area_id,
        )

        # Child_1
        tap_measure_child_1 = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=valid_between,
            goods_nomenclature=tap_child_goods_nomenclature_1,
            geographical_area=tap_geo_area,
        )

        tap_duty_expression = DutyExpressionFactory.create(
            duty_amount_applicability_code=1,
            valid_between=TaricDateRange(date(2000, 1, 1)),
            prefix="",
            measurement_unit_applicability_code=0,
            monetary_unit_applicability_code=0,
            description="% or amount",
        )

        tap_measure_component = MeasureComponentFactory.create(
            component_measure=tap_measure_child_1,
            duty_amount=12.0,
            duty_expression=tap_duty_expression,
        )

        target = RateChecks(ref_rate=ref_rate)
        assert target.run_check() == (
            AlignmentReportCheckStatus.FAIL,
            f"{comm_code} : no expected measures found on good code or children",
        )

    def test_run_check_warning_multiple_matches(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        ref_rate = RefRateFactory.create(
            duty_rate="12%",
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        tap_goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_rate.commodity_code,
            valid_between=valid_between,
        )

        tap_geo_area = GeographicalAreaFactory.create(
            area_id=area_id,
        )

        tap_measure = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=valid_between,
            goods_nomenclature=tap_goods_nomenclature,
            geographical_area=tap_geo_area,
        )

        tap_duty_expression = DutyExpressionFactory.create(
            duty_amount_applicability_code=1,
            valid_between=TaricDateRange(date(2000, 1, 1)),
            prefix="",
            measurement_unit_applicability_code=0,
            monetary_unit_applicability_code=0,
            description="% or amount",
        )

        tap_measure_component = MeasureComponentFactory.create(
            component_measure=tap_measure,
            duty_amount=12.0,
            duty_expression=tap_duty_expression,
        )

        tap_measure = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=valid_between,
            goods_nomenclature=tap_goods_nomenclature,
            geographical_area=tap_geo_area,
        )

        tap_measure_component = MeasureComponentFactory.create(
            component_measure=tap_measure,
            duty_amount=12.0,
            duty_expression=tap_duty_expression,
        )

        target = RateChecks(ref_rate=ref_rate)
        assert target.run_check() == (
            AlignmentReportCheckStatus.WARNING,
            f"{ref_rate.commodity_code} : multiple measures match",
        )
