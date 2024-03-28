import pytest

from common.tests.factories import GeographicalAreaFactory
from reference_documents.models import ReferenceDocument

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestReferenceDocumentVersion:
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
