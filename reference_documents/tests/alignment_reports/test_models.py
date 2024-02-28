import pytest

from reference_documents.models import AlignmentReport

pytestmark = pytest.mark.django_db


class TestAlignmentReport:
    def test_create_with_defaults(self):
        subject = AlignmentReport.objects.create()

        subject.save()
        assert subject.reference_document_version.count() == 0
        assert subject.created_at is not None
