import pytest

from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestReferenceDocumentVersion:
    def test_create_with_defaults(self):
        target = factories.ReferenceDocumentVersionFactory()

        assert target.created_at is not None
        assert target.updated_at is not None
        assert target.version is not None
        assert target.published_date is not None
        assert target.entry_into_force_date is not None
        assert target.reference_document is not None
        assert target.status is not None

    def test_preferential_quotas(self):
        target = factories.ReferenceDocumentVersionFactory.create()
        # add a pref quota
        factories.PreferentialQuotaFactory.create(
            preferential_quota_order_number__reference_document_version=target,
        )

        assert len(target.preferential_quotas()) == 1
