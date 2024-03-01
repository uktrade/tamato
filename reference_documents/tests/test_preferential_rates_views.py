import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


def test_get_without_permissions(valid_user, client):
    valid_user.user_permissions.add(
        Permission.objects.get(codename="change_preferentialrate"),
    )
    client.force_login(valid_user)
    pref_rate = factories.PreferentialRateFactory.create()

    response = client.get(
        reverse(
            "reference_documents:preferential_rates_edit",
            kwargs={"pk": pref_rate.pk},
        ),
    )

    assert response.status_code == 200


@pytest.mark.reference_documents
class TestPreferentialRateEditView:
    def test_get_without_permissions(self, valid_user, client):
        valid_user.user_permissions.add(
            Permission.objects.get(codename="change_preferentialrate"),
        )
        client.force_login(valid_user)
        pref_rate = factories.PreferentialRateFactory.create()

        response = client.get(
            reverse(
                "reference_documents:preferential_rates_edit",
                kwargs={"pk": pref_rate.pk},
            ),
        )

        assert response.status_code == 200

    def test_get_with_permissions(self, superuser_client):
        pref_rate = factories.PreferentialRateFactory.create()

        response = superuser_client.get(
            reverse(
                "reference_documents:preferential_rates_edit",
                kwargs={"pk": pref_rate.pk},
            ),
        )
        assert response.status_code == 200

    def test_ref_doc_create_creates_object_and_redirects(self, valid_user, client):
        """Tests that posting the reference document create form adds the new
        reference document to the database and redirects to the confirm-create
        page."""
        valid_user.user_permissions.add(
            Permission.objects.get(codename="change_preferentialrate"),
        )
        client.force_login(valid_user)
        pref_rate = factories.PreferentialRateFactory.create()
        create_url = reverse(
            "reference_documents:preferential_rates_edit",
            kwargs={"pk": pref_rate.pk},
        )
        response = client.get(create_url)
        assert response.status_code == 302

        # ref_doc = ReferenceDocument.objects.get(title=form_data["title"])
        # assert ref_doc
        # assert response.url == reverse(
        #     "reference_documents:confirm-create",
        #     kwargs={"pk": ref_doc.pk},
        # )


class TestPreferentialRateDeleteView:
    pass
