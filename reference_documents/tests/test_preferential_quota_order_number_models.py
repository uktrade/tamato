import pytest

from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.tests.factories import PreferentialQuotaOrderNumberFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumber:
    def test_init(self):
        target = PreferentialQuotaOrderNumber()

        assert target.quota_order_number == ""
        assert target.coefficient is None
        assert target.main_order_number is None
        assert target.valid_between is None

    def test_str(self):
        target = PreferentialQuotaOrderNumberFactory.create()

        assert str(target) == f"{target.quota_order_number}"
