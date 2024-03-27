import pytest

from reference_documents.models import PreferentialRate

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRate:
    def test_init(self):
        target = PreferentialRate()
        assert target.commodity_code == ""
        assert target.duty_rate == ""
        assert target.order is None
        assert target.reference_document_version is None
        assert target.valid_between is None
