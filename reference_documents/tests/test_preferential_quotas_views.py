import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaEditView:
    def test_get_without_permissions(self, valid_user_client):
        pref_quota = factories.PreferentialQuotaFactory.create()

        response = valid_user_client.get(
            reverse(
                "reference_documents:preferential_quotas_edit",
                kwargs={"pk": pref_quota.pk},
            ),
        )
        assert response.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        pref_quota = factories.PreferentialQuotaFactory.create()

        response = superuser_client.get(
            reverse(
                "reference_documents:preferential_quotas_edit",
                kwargs={"pk": pref_quota.pk},
            ),
        )
        assert response.status_code == 200


@pytest.mark.reference_documents
def test_quota_bulk_create_creates_object_and_redirects(valid_user, client):
    """Test that posting the bulk create from creates all preferential quotas
    and redirects."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="add_preferentialquota"),
    )
    client.force_login(valid_user)

    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_quota_order_number = (
        factories.PreferentialQuotaOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
    )
    assert not ref_doc_version.preferential_quotas()

    data = {
        "preferential_quota_order_number": preferential_quota_order_number.pk,
        "commodity_codes": "1234567890\r\n2345678901",
        "quota_duty_rate": "5%",
        "measurement": "KG",
        "start_date_0_0": "1",
        "start_date_0_1": "1",
        "start_date_0_2": "2023",
        "end_date_0_0": "31",
        "end_date_0_1": "12",
        "end_date_0_2": "2023",
        "volume_0": "500",
        "start_date_1_0": "1",
        "start_date_1_1": "1",
        "start_date_1_2": "2024",
        "end_date_1_0": "31",
        "end_date_1_1": "12",
        "end_date_1_2": "2024",
        "volume_1": "400",
        "start_date_2_0": "1",
        "start_date_2_1": "1",
        "start_date_2_2": "2025",
        "end_date_2_0": "31",
        "end_date_2_1": "12",
        "end_date_2_2": "2025",
        "volume_2": "300",
    }

    create_url = reverse(
        "reference_documents:preferential_quotas_bulk_create_for_order",
        kwargs={
            "pk": ref_doc_version.pk,
            "order_pk": preferential_quota_order_number.pk,
        },
    )
    response = client.get(create_url)
    assert response.status_code == 200

    response = client.post(create_url, data)
    assert response.status_code == 302
    new_preferential_quotas = ref_doc_version.preferential_quotas()
    assert len(new_preferential_quotas) == 6
    assert (
        response.url
        == reverse(
            "reference_documents:version-details",
            args=[ref_doc_version.pk],
        )
        + "#tariff-quotas"
    )


@pytest.mark.reference_documents
def test_quota_bulk_create_invalid(valid_user, client):
    """Test that posting the bulk create form with invalid data fails and
    reloads the form with errors."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="add_preferentialquota"),
    )
    client.force_login(valid_user)

    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_quota_order_number = (
        factories.PreferentialQuotaOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
    )
    assert not ref_doc_version.preferential_quotas()

    data = {
        "preferential_quota_order_number": preferential_quota_order_number.pk,
        "commodity_codes": "1234567890\r\n2345678901\r\n12345678910",
        "quota_duty_rate": "",
        "measurement": "",
        "start_date_0_0": "1",
        "start_date_0_1": "1",
        "start_date_0_2": "2023",
        "end_date_0_0": "31",
        "end_date_0_1": "12",
        "end_date_0_2": "2023",
        "volume_0": "500",
        "start_date_1_0": "1",
        "start_date_1_1": "1",
        "start_date_1_2": "2024",
        "end_date_1_0": "31",
        "end_date_1_1": "12",
        "end_date_1_2": "2022",
        "volume_1": "400",
        "start_date_2_0": "",
        "start_date_2_1": "1",
        "start_date_2_2": "2025",
        "end_date_2_0": "31",
        "end_date_2_1": "12",
        "end_date_2_2": "2025",
        "volume_2": "300",
    }

    create_url = reverse(
        "reference_documents:preferential_quotas_bulk_create",
        kwargs={"pk": ref_doc_version.pk},
    )

    response = client.post(create_url, data)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    error_messages = soup.select("ul.govuk-list.govuk-error-summary__list a")

    assert "Duty rate is required" == error_messages[0].text
    assert "Measurement is required" in error_messages[1].text
    assert "Enter the day, month and year" in error_messages[2].text
    assert (
        "Ensure all commodity codes are 10 digits and each on a new line"
        in error_messages[3].text
    )
    assert (
        "The end date must be the same as or after the start date"
        in error_messages[4].text
    )

    new_preferential_quotas = ref_doc_version.preferential_quotas()
    assert len(new_preferential_quotas) == 0


@pytest.mark.reference_documents
def test_quota_bulk_create_without_permission(valid_user_client):
    """Test that posting the bulk create form without relevant user permissions
    does not work."""
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_quota_order_number = (
        factories.PreferentialQuotaOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
    )
    assert not ref_doc_version.preferential_quotas()

    data = {
        "preferential_quota_order_number": preferential_quota_order_number.pk,
        "commodity_codes": "1234567890\r\n2345678901",
        "quota_duty_rate": "5%",
        "measurement": "KG",
        "start_date_0_0": "1",
        "start_date_0_1": "1",
        "start_date_0_2": "2023",
        "end_date_0_0": "31",
        "end_date_0_1": "12",
        "end_date_0_2": "2023",
        "volume_0": "500",
        "start_date_1_0": "1",
        "start_date_1_1": "1",
        "start_date_1_2": "2024",
        "end_date_1_0": "31",
        "end_date_1_1": "12",
        "end_date_1_2": "2024",
        "volume_1": "400",
        "start_date_2_0": "1",
        "start_date_2_1": "1",
        "start_date_2_2": "2025",
        "end_date_2_0": "31",
        "end_date_2_1": "12",
        "end_date_2_2": "2025",
        "volume_2": "300",
    }

    create_url = reverse(
        "reference_documents:preferential_quotas_bulk_create",
        kwargs={"pk": ref_doc_version.pk},
    )

    response = valid_user_client.post(create_url, data)
    assert response.status_code == 403
    assert not ref_doc_version.preferential_quotas()
