import pytest

from reference_documents.models import PreferentialQuota, ReferenceDocumentVersionStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuota:
    def test_init(self):
        target = PreferentialQuota()

        assert target.preferential_quota_order_number is None
        assert target.commodity_code == ""
        assert target.quota_duty_rate == ""
        assert target.volume == ""
        assert target.valid_between is None
        assert target.measurement == ""

    def test_state_not_editable_prevents_save(self):
        target = factories.PreferentialQuotaFactory()
        target_original_volume = target.volume
        rdv = target.preferential_quota_order_number.reference_document_version

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert rdv.editable()

        rdv.in_review()
        rdv.save(force_save=True)

        target.volume = '999999999'
        target.save()

        target.refresh_from_db()

        assert float(target_original_volume) == float(target.volume)

        rdv.published()
        rdv.save(force_save=True)

        target.volume = '999999999'
        target.save()

        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not rdv.editable()
        assert float(target_original_volume) == float(target.volume)
