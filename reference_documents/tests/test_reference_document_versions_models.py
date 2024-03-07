import pytest

from common.tests.factories import GeographicalAreaDescriptionFactory
from common.tests.factories import GeographicalAreaFactory
from geo_areas.models import GeographicalAreaDescription
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


@pytest.mark.reference_documents
def test_get_area_name_by_area_id():
    ref_doc = factories.ReferenceDocumentFactory.create(area_id="BE")
    geo_area = GeographicalAreaFactory.create(area_id="BE")
    GeographicalAreaDescriptionFactory(described_geographicalarea=geo_area)

    ref_doc_area_name = ref_doc.get_area_name_by_area_id()
    geo_area_description = (
        GeographicalAreaDescription.objects.latest_approved()
        .filter(described_geographicalarea__area_id=geo_area.area_id)
        .order_by("-validity_start")
        .first()
    )
    assert ref_doc_area_name == geo_area_description.description
