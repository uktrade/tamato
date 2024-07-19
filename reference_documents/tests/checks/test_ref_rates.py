import pytest

from reference_documents.check.base import BaseRateCheck
from reference_documents.models import AlignmentReportCheckStatus


@pytest.mark.reference_documents
class RateExists(BaseRateCheck):
    @pytest.mark.skip(reason="test not implemented yet")
    def test_run_check(self):
        pass