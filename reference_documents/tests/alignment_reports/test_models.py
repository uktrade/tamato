import pytest

from reference_documents.tests.factories import AlignmentReportFactory

pytestmark = pytest.mark.django_db


class TestAlignmentReport:
    def test_create_with_defaults(self):
        target = AlignmentReportFactory()
        assert target.created_at is not None
