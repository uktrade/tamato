import pytest

from reference_documents.models import PreferentialQuota

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
        assert target.order is None
