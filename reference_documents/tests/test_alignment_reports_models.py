import pytest

from reference_documents.tests.factories import AlignmentReportCheckFactory
from reference_documents.tests.factories import AlignmentReportFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestAlignmentReport:
    def test_create_with_defaults(self):
        target = AlignmentReportFactory()
        assert target.created_at is not None
        assert target.reference_document_version is not None


@pytest.mark.reference_documents
class TestAlignmentReportCheck:
    def test_create_with_defaults(self):
        target = AlignmentReportCheckFactory()

        assert target.created_at is not None
        assert target.alignment_report is not None
        assert target.check_name is not None
        assert target.status is not None
        assert target.message is not None
        assert target.preferential_quota is None
        assert target.preferential_rate is None
