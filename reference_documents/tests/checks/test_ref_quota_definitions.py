from datetime import date

import pytest

from common.tests.factories import QuotaOrderNumberFactory, QuotaDefinitionFactory, GoodsNomenclatureFactory, MeasureFactory
from common.util import TaricDateRange
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.ref_order_numbers import OrderNumberChecks
from reference_documents.check.ref_quota_definitions import QuotaDefinitionExists
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestQuotaDefinitionExists:

    def test_run_check_passed(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        # setup TAP objects
        tap_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_quota_definition.ref_order_number.order_number,
            valid_between=valid_between,
            order_number__valid_between=valid_between,
        )

        goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
        )

        tap_measure = MeasureFactory.create(
            measure_type__sid=143,
            valid_between=valid_between,
            goods_nomenclature=goods_nomenclature,
            order_number=tap_quota_definition.order_number,
            geographical_area__area_id=area_id,
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.PASS, '')

    def test_run_check_fails_no_measure(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        # setup TAP objects
        tap_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_quota_definition.ref_order_number.order_number,
            valid_between=valid_between,
            order_number__valid_between=valid_between,
        )

        goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - measure(s) spanning whole quota definition period not found')

    def test_run_check_fails_no_quota_definition(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - quota definition not found')

    def test_run_check_fails_no_goods_nomenclature(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - commodity code not found')
