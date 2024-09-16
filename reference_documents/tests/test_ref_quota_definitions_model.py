import pytest

from reference_documents.models import ReferenceDocumentVersionStatus
from reference_documents.models import RefQuotaDefinition
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaDefinition:
    def test_init(self):
        target = RefQuotaDefinition()

        assert target.ref_order_number is None
        assert target.commodity_code == ""
        assert target.duty_rate == ""
        assert target.volume == ""
        assert target.valid_between is None
        assert target.measurement == ""

    def test_state_not_editable_prevents_save(self):
        target = factories.RefQuotaDefinitionFactory()
        target_original_volume = target.volume
        rdv = target.ref_order_number.reference_document_version

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert rdv.editable()

        rdv.in_review()
        rdv.save(force_save=True)

        target.volume = "999999999"
        target.save()

        target.refresh_from_db()

        assert float(target_original_volume) == float(target.volume)

        rdv.published()
        rdv.save(force_save=True)

        target.volume = "999999999"
        target.save()

        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not rdv.editable()
        assert float(target_original_volume) == float(target.volume)
