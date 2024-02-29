import pytest

from reference_documents.tests.factories import ReferenceDocumentVersionFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestReferenceDocumentVersion:
    def test_create_with_defaults(self):
        target = ReferenceDocumentVersionFactory()

        assert target.created_at is not None
        assert target.updated_at is not None
        assert target.version is not None
        assert target.published_date is not None
        assert target.entry_into_force_date is not None
        assert target.reference_document is not None
        assert target.status is not None
