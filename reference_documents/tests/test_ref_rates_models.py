import pytest

from reference_documents.models import RefRate, ReferenceDocumentVersionStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRate:
    def test_init(self):
        target = RefRate()
        assert target.commodity_code == ""
        assert target.duty_rate == ""
        assert target.reference_document_version is None
        assert target.valid_between is None

    def test_state_not_editable_prevents_save(self):
        target = factories.RefRateFactory()
        target_original_duty_rate = target.duty_rate
        rdv = target.reference_document_version

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert rdv.editable()

        rdv.in_review()
        rdv.save(force_save=True)

        target.duty_rate = '99.77%'
        target.save()

        target.refresh_from_db()

        assert target_original_duty_rate == target.duty_rate

        rdv.published()
        rdv.save(force_save=True)

        target.duty_rate = '99.77%'
        target.save()

        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not rdv.editable()
        assert target_original_duty_rate == target.duty_rate

