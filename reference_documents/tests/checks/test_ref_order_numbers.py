from datetime import date

import pytest

from common.tests.factories import QuotaOrderNumberFactory
from common.util import TaricDateRange
from reference_documents.check.ref_order_numbers import OrderNumberChecks
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestOrderNumberExists:

    def test_run_check_passed(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        # setup TAP objects
        tap_order_number = QuotaOrderNumberFactory.create(
            order_number=ref_order_number.order_number,
            valid_between=valid_between,
        )

        target = OrderNumberChecks(ref_order_number=ref_order_number)
        assert target.run_check() == (AlignmentReportCheckStatus.PASS, "")

    def test_run_check_fail_no_order_validity_range(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=None,
        )

        # setup TAP objects
        tap_order_number = QuotaOrderNumberFactory.create(
            order_number=ref_order_number.order_number,
            valid_between=valid_between,
        )

        target = OrderNumberChecks(ref_order_number=ref_order_number)
        assert target.run_check() == (
            AlignmentReportCheckStatus.FAIL,
            f"order number {tap_order_number.order_number} cant be checked, no validity date range",
        )

    def test_run_check_fail_order_number_does_not_exist(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        target = OrderNumberChecks(ref_order_number=ref_order_number)
        assert target.run_check() == (
            AlignmentReportCheckStatus.FAIL,
            f"order number not found matching {ref_order_number.order_number}",
        )
