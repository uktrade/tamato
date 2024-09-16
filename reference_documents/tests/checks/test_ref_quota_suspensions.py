from datetime import date

import pytest

from common.tests.factories import MeasureFactory, GoodsNomenclatureFactory, QuotaDefinitionFactory, QuotaSuspensionFactory
from common.util import TaricDateRange
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.ref_quota_definitions import QuotaDefinitionChecks
from reference_documents.check.ref_quota_suspensions import QuotaSuspensionChecks
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db

@pytest.mark.reference_documents
class TestQuotaSuspensionExists:

   def test_run_check_passed(self):
      valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
      valid_between_suspension = TaricDateRange(date(2020, 2, 1), date(2020, 6, 30))
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

      ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
         ref_quota_definition=ref_quota_definition,
         valid_between=valid_between_suspension
      )

      # setup TAP objects
      tap_quota_definition = QuotaDefinitionFactory.create(
         order_number__order_number=ref_quota_definition.ref_order_number.order_number,
         valid_between=valid_between,
         order_number__valid_between=valid_between,
      )

      tap_quota_suspension = QuotaSuspensionFactory.create(
         quota_definition=tap_quota_definition,
         valid_between=valid_between_suspension
      )

      tap_goods_nomenclature = GoodsNomenclatureFactory.create(
         item_id=ref_quota_definition.commodity_code,
         valid_between=valid_between,
      )

      tap_measure = MeasureFactory.create(
         measure_type__sid=143,
         valid_between=valid_between,
         goods_nomenclature=tap_goods_nomenclature,
         order_number=tap_quota_definition.order_number,
         geographical_area__area_id=area_id,
      )

      target = QuotaSuspensionChecks(ref_quota_suspension=ref_quota_suspension)
      assert target.run_check() == (AlignmentReportCheckStatus.PASS, '')

   def test_run_check_failed_no_suspension(self):
      valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
      valid_between_suspension = TaricDateRange(date(2020, 2, 1), date(2020, 6, 30))
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

      ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
         ref_quota_definition=ref_quota_definition,
         valid_between=valid_between_suspension
      )

      # setup TAP objects
      tap_quota_definition = QuotaDefinitionFactory.create(
         order_number__order_number=ref_quota_definition.ref_order_number.order_number,
         valid_between=valid_between,
         order_number__valid_between=valid_between,
      )

      tap_goods_nomenclature = GoodsNomenclatureFactory.create(
         item_id=ref_quota_definition.commodity_code,
         valid_between=valid_between,
      )

      tap_measure = MeasureFactory.create(
         measure_type__sid=143,
         valid_between=valid_between,
         goods_nomenclature=tap_goods_nomenclature,
         order_number=tap_quota_definition.order_number,
         geographical_area__area_id=area_id,
      )

      target = QuotaSuspensionChecks(ref_quota_suspension=ref_quota_suspension)
      assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - quota suspension not found')

   def test_run_check_failed_suspension_valid_between_different(self):
      valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
      valid_between_suspension = TaricDateRange(date(2020, 2, 1), date(2020, 6, 30))
      valid_between_suspension_tap = TaricDateRange(date(2020, 2, 5), date(2020, 6, 30))
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

      ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
         ref_quota_definition=ref_quota_definition,
         valid_between=valid_between_suspension
      )

      # setup TAP objects
      tap_quota_definition = QuotaDefinitionFactory.create(
         order_number__order_number=ref_quota_definition.ref_order_number.order_number,
         valid_between=valid_between,
         order_number__valid_between=valid_between,
      )

      tap_quota_suspension = QuotaSuspensionFactory.create(
         quota_definition=tap_quota_definition,
         valid_between=valid_between_suspension_tap
      )

      tap_goods_nomenclature = GoodsNomenclatureFactory.create(
         item_id=ref_quota_definition.commodity_code,
         valid_between=valid_between,
      )

      tap_measure = MeasureFactory.create(
         measure_type__sid=143,
         valid_between=valid_between,
         goods_nomenclature=tap_goods_nomenclature,
         order_number=tap_quota_definition.order_number,
         geographical_area__area_id=area_id,
      )

      target = QuotaSuspensionChecks(ref_quota_suspension=ref_quota_suspension)
      assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - quota suspension not found')