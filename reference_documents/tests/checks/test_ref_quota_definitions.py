from datetime import date

import pytest

from common.util import TaricDateRange
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.ref_quota_definitions import QuotaDefinitionExists
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories


@pytest.mark.reference_documents
class PreferentialQuotaExists(BaseQuotaDefinitionCheck):
    @pytest.mark.skip(reason="test not implemented yet")
    def run_check(self):
        pass

    def test_run_check_fail_order_number_does_not_exist(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            valid_between=valid_between,
            ref_order_number__valid_between=valid_between
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, f'FAIL - order number  not found')
    #
    #
    # if not self.tap_order_number():
    #     message = f"FAIL - order number  not found"
    #     print(message)
    #     return AlignmentReportCheckStatus.FAIL, message
    #
    # elif not self.geo_area():
    #     message = f"FAIL - geo area not found"
    #     print(message)
    #     return AlignmentReportCheckStatus.FAIL, message
    #
    # elif not self.commodity_code():
    #     message = f"FAIL - commodity code not found"
    #     print(message)
    #     return AlignmentReportCheckStatus.FAIL, message
    #
    # elif not self.quota_definition():
    #     message = f"FAIL - quota definition not found"
    #     print(message)
    #     return AlignmentReportCheckStatus.FAIL, message
    #
    # elif not self.measures():
    #     message = (
    #         f"FAIL - measure(s) spanning whole quota definition period not found"
    #     )
    #     print(message)
    #     return AlignmentReportCheckStatus.FAIL, message
    # else:
    #     return AlignmentReportCheckStatus.PASS, ''