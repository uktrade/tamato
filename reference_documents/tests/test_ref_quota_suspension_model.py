import pytest

from reference_documents.models import RefQuotaDefinition, ReferenceDocumentVersionStatus, RefQuotaSuspension
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaSuspension:
    def test_init(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()
        target = RefQuotaSuspension(ref_quota_definition=ref_quota_definition)

        assert target.ref_quota_definition is ref_quota_definition
        assert target.valid_between is None

    def test_state_not_editable_prevents_save(self):
        target = factories.RefQuotaSuspensionFactory()
        rdv = target.ref_quota_definition.ref_order_number.reference_document_version

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert rdv.editable()

        rdv.in_review()
        rdv.save(force_save=True)

        target.save()

        target.refresh_from_db()

        rdv.published()
        rdv.save(force_save=True)

        target.save()
        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not rdv.editable()
