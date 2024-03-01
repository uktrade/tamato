import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRateEditView:
    @pytest.mark.parametrize(
        "has_permissions, user_type, expected_http_status",
        [
            (["change_preferentialrate"], "regular", 200),
            ([], "regular", 403),
            ([], "superuser", 200),
        ],
    )
    def test_get(
        self,
        valid_user,
        superuser,
        client,
        has_permissions,
        user_type,
        expected_http_status,
    ):
        if user_type == "superuser":
            user = superuser
        else:
            user = valid_user

            for permission in has_permissions:
                user.user_permissions.add(
                    Permission.objects.get(codename=permission),
                )

        client.force_login(user)
        pref_rate = factories.PreferentialRateFactory.create()

        response = client.get(
            reverse(
                "reference_documents:preferential_rates_edit",
                kwargs={"pk": pref_rate.pk},
            ),
        )

        assert response.status_code == expected_http_status


@pytest.mark.reference_documents
class TestPreferentialRateDeleteView:
    pass
