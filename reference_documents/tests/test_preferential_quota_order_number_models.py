import pytest

from reference_documents.models import PreferentialQuotaOrderNumber, ReferenceDocumentVersionStatus
from reference_documents.tests import factories
from reference_documents.tests.factories import PreferentialQuotaOrderNumberFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumber:
    def test_init(self):
        target = PreferentialQuotaOrderNumber()

        assert target.quota_order_number == ""
        assert target.coefficient is None
        assert target.main_order_number is None
        assert target.valid_between is None

    def test_str(self):
        target = PreferentialQuotaOrderNumberFactory.create()

        assert str(target) == f"{target.quota_order_number}"

    def test_state_not_editable_prevents_save(self):
        target = factories.PreferentialQuotaOrderNumberFactory()
        target_original_quota_order_number = target.quota_order_number
        rdv = target.reference_document_version

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert rdv.editable()

        rdv.in_review()
        rdv.save(force_save=True)

        target.quota_order_number = '123123'
        target.save()

        target.refresh_from_db()

        assert target.quota_order_number == target_original_quota_order_number

        rdv.published()
        rdv.save(force_save=True)

        target.quota_order_number = '123123'
        target.save()

        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not rdv.editable()
        assert target.quota_order_number == target_original_quota_order_number

