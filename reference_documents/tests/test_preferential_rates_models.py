import pytest

from reference_documents.tests.factories import PreferentialRateFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRate:
    def test_create_with_defaults(self):
        target = PreferentialRateFactory()
        assert target.commodity_code is not None
        assert target.duty_rate is not None
        assert target.order is not None
        assert target.reference_document_version is not None
        assert target.valid_between is not None
