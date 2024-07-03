import pytest

from reference_documents.check.base import BaseOrderNumberCheck
from reference_documents.models import AlignmentReportCheckStatus


@pytest.mark.reference_documents
class TestOrderNumberExists(BaseOrderNumberCheck):
    @pytest.mark.skip(reason="test not implemented yet")
    def test_run_check(self):
        pass
