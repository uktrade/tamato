import pytest
from reference_documents.check.ref_order_numbers import *
from reference_documents.check.ref_quota_definitions import *
from reference_documents.check.ref_rates import *
from reference_documents.check.utils import Utils
from reference_documents.models import AlignmentReport
from reference_documents.models import AlignmentReportCheck
from reference_documents.models import ReferenceDocumentVersion


@pytest.mark.reference_documents
class TestChecks:
    @pytest.mark.skip(reason="test not implemented yet")
    def test_init(self):
        pass

    @pytest.mark.skip(reason="test not implemented yet")
    def test_get_checks_for(self):
        pass

    @pytest.mark.skip(reason="test not implemented yet")
    def test_run(self):
        pass

    @pytest.mark.skip(reason="test not implemented yet")
    def test_capture_check_result(self):
        pass
