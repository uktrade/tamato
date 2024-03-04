import pytest
from django.urls import reverse

from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


class TestPreferentialQuotaEditView:
    def test_get_without_permissions(self, valid_user_client):
        pref_quota = factories.PreferentialQuotaFactory.create()

        response = valid_user_client.get(
            reverse(
                "reference_documents:preferential_quotas_edit",
                kwargs={"pk": pref_quota.pk},
            ),
        )
        assert response.status_code == 200

    def test_get_with_permissions(self, superuser_client):
        pref_quota = factories.PreferentialQuotaFactory.create()

        response = superuser_client.get(
            reverse(
                "reference_documents:preferential_quotas_edit",
                kwargs={"pk": pref_quota.pk},
            ),
        )
        assert response.status_code == 200
