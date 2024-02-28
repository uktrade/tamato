import pytest

from reference_documents.tests.factories import ReferenceDocumentFactory

pytestmark = pytest.mark.django_db


class TestReferenceDocumentVersion:
    def test_create_with_defaults(self):
        target = ReferenceDocumentFactory()

        assert target.created_at is not None
        assert target.title is not None
        assert target.area_id is not None
