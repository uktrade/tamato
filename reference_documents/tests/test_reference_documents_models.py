import pytest

from common.tests.factories import GeographicalAreaFactory
from reference_documents.models import ReferenceDocument, ReferenceDocumentVersionStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestReferenceDocument:
    def test_init(self):
        target = ReferenceDocument()

        assert target.created_at is None
        assert target.title == ""
        assert target.area_id == ""

    def test_get_area_name_by_area_id_no_match_to_database(self):
        target = ReferenceDocument()

        assert target.get_area_name_by_area_id() == " (unknown description)"

    def test_get_area_name_by_area_id_match_to_database(self):
        GeographicalAreaFactory.create(
            area_id="TEST",
            description__description="test description",
        )
        target = ReferenceDocument(area_id="TEST")

        assert target.get_area_name_by_area_id() == "test description"

    def test_state_not_editable_prevents_save(self):
        rdv = factories.ReferenceDocumentVersionFactory()
        target = rdv.reference_document

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert target.editable()

        rdv = target.reference_document_versions.first()
        rdv.in_review()
        rdv.save(force_save=True)
        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.IN_REVIEW
        assert not target.editable()

        rdv.published()
        rdv.save(force_save=True)

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not target.editable()

        area_id = target.area_id

        target.area_id = 'zz'
        target.save()

        rd = ReferenceDocument.objects.get(pk=target.pk)

        assert rd.area_id == area_id
