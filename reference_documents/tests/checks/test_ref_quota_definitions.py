import pytest

from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.models import AlignmentReportCheckStatus


@pytest.mark.reference_documents
class PreferentialQuotaExists(BaseQuotaDefinitionCheck):
    @pytest.mark.skip(reason="test not implemented yet")
    def run_check(self):
        pass