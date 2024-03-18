import pytest

from reference_documents.tests.factories import PreferentialQuotaFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuota:
    def test_create_with_defaults(self):
        target = PreferentialQuotaFactory()

        assert target.preferential_quota_order_number is not None
        assert target.commodity_code is not None
        assert target.quota_duty_rate is not None
        assert target.volume is not None
        assert target.valid_between is not None
        assert target.measurement is not None
        assert target.order is not None
