import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.forms.preferential_rate_forms import (
    PreferentialRateCreateUpdateForm,
)
from reference_documents.models import PreferentialRate
from reference_documents.tests import factories
from reference_documents.views.preferential_rate_views import PreferentialRateCreate
from reference_documents.views.preferential_rate_views import PreferentialRateEdit

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRateEditView:
    @pytest.mark.parametrize(
        "user_type, expected_http_status",
        [
            ("regular", 403),
            ("superuser", 200),
        ],
    )
    def test_get(
        self,
        valid_user,
        superuser,
        client,
        user_type,
        expected_http_status,
    ):
        if user_type == "superuser":
            user = superuser
        else:
            user = valid_user

        client.force_login(user)
        pref_rate = factories.PreferentialRateFactory.create()

        resp = client.get(
            reverse(
                "reference_documents:preferential_rates_edit",
                kwargs={"pk": pref_rate.pk},
            ),
        )

        assert resp.status_code == expected_http_status

    def test_success_url(self):
        pref_rate = factories.PreferentialRateFactory.create()

        target = PreferentialRateEdit()
        target.object = pref_rate
        assert target.get_success_url() == reverse(
            "reference_documents:version-details",
            args=[target.object.reference_document_version.pk],
        )

    def test_form_valid(self):
        pref_rate = factories.PreferentialRateFactory.create()
        target = PreferentialRateEdit()
        target.object = pref_rate

        form = PreferentialRateCreateUpdateForm(
            data={
                "start_date_0": 1,
                "start_date_1": 1,
                "start_date_2": 2024,
                "commodity_code": "0100000000",
                "duty_rate": "10%",
            },
            instance=target.object,
        )

        assert form.is_valid()
        assert target.form_valid(form)

    def test_form_invalid(self):
        pref_rate = factories.PreferentialRateFactory.create()
        target = PreferentialRateEdit()
        target.object = pref_rate

        form = PreferentialRateCreateUpdateForm(
            data={
                "start_date_0": 1,
                "start_date_1": 1,
                "start_date_2": 2024,
                "commodity_code": "",
                "duty_rate": "",
            },
            instance=target.object,
        )

        assert not form.is_valid()

        with pytest.raises(ValueError):
            target.form_valid(form)


@pytest.mark.reference_documents
class TestPreferentialRateCreate:
    @pytest.mark.parametrize(
        "user_type, expected_http_status",
        [
            ("regular", 403),
            ("superuser", 200),
        ],
    )
    def test_get(
        self,
        valid_user,
        superuser,
        client,
        user_type,
        expected_http_status,
    ):
        if user_type == "superuser":
            user = superuser
        else:
            user = valid_user

        client.force_login(user)
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create()

        resp = client.get(
            reverse(
                "reference_documents:preferential_rates_create",
                kwargs={"version_pk": ref_doc_ver.pk},
            ),
        )

        assert resp.status_code == expected_http_status

    def test_success_url(self):
        pref_rate = factories.PreferentialRateFactory.create()
        target = PreferentialRateCreate()
        target.object = pref_rate
        assert target.get_success_url() == reverse(
            "reference_documents:version-details",
            args=[target.object.reference_document_version.pk],
        )

    @pytest.mark.parametrize(
        "user_type, expected_http_status",
        [
            ("regular", 403),
            ("superuser", 302),
        ],
    )
    def test_post(
        self,
        valid_user,
        superuser,
        client,
        user_type,
        expected_http_status,
    ):
        if user_type == "superuser":
            user = superuser
        else:
            user = valid_user

        client.force_login(user)
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create()

        post_data = {
            "reference_document_version": ref_doc_ver.pk,
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2024,
            "commodity_code": "1231231230",
            "duty_rate": "12.5%",
        }

        resp = client.post(
            reverse(
                "reference_documents:preferential_rates_create",
                kwargs={"version_pk": ref_doc_ver.pk},
            ),
            data=post_data,
        )

        assert resp.status_code == expected_http_status


@pytest.mark.reference_documents
class TestPreferentialRateDeleteView:
    @pytest.mark.parametrize(
        "http_method, expected_http_status",
        [
            ("get", 200),
            ("post", 302),
        ],
    )
    def test_get_without_permissions(
        self,
        superuser_client,
        http_method,
        expected_http_status,
    ):
        pref_rate = factories.PreferentialRateFactory.create()

        client = superuser_client

        resp = getattr(client, http_method)(
            reverse(
                "reference_documents:preferential_rates_delete",
                kwargs={
                    "pk": pref_rate.pk,
                },
            ),
        )
        assert resp.status_code == expected_http_status

    @pytest.mark.parametrize(
        "http_method, expected_http_status",
        [
            ("get", 403),
            ("post", 403),
        ],
    )
    def test_regular_user_get_post(
        self,
        valid_user_client,
        http_method,
        expected_http_status,
    ):
        pref_rate = factories.PreferentialRateFactory.create()

        client = valid_user_client

        resp = getattr(client, http_method)(
            reverse(
                "reference_documents:preferential_rates_delete",
                kwargs={
                    "pk": pref_rate.pk,
                },
            ),
        )
        assert resp.status_code == expected_http_status


@pytest.mark.reference_documents
def test_preferential_rate_bulk_create_creates_object_and_redirects(valid_user, client):
    """Test that posting the bulk create from creates all preferential rates and
    redirects."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="add_preferentialrate"),
    )
    client.force_login(valid_user)

    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_rates = PreferentialRate.objects.all().filter(
        reference_document_version=ref_doc_version,
    )
    assert len(preferential_rates) == 0

    data = {
        "commodity_codes": "1234567890\r\n2345678901\r\n3456789012\r\n4567890123",
        "duty_rate": "5%",
        "start_date_0": "1",
        "start_date_1": "1",
        "start_date_2": "2023",
        "end_date_0": "31",
        "end_date_1": "12",
        "end_date_2": "2023",
    }

    create_url = reverse(
        "reference_documents:preferential_rates_bulk_create",
        kwargs={"pk": ref_doc_version.pk},
    )
    resp = client.get(create_url)
    assert resp.status_code == 200
    resp = client.post(create_url, data)
    assert resp.status_code == 302
    preferential_rates = PreferentialRate.objects.all().filter(
        reference_document_version=ref_doc_version,
    )
    assert len(preferential_rates) == 4
    assert resp.url == reverse(
        "reference_documents:version-details",
        args=[ref_doc_version.pk],
    )


@pytest.mark.reference_documents
def test_preferential_rate_bulk_create_invalid(valid_user, client):
    """Test that posting the bulk create form with invalid data fails and
    reloads the form with errors."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="add_preferentialrate"),
    )
    client.force_login(valid_user)

    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_rates = PreferentialRate.objects.all().filter(
        reference_document_version=ref_doc_version,
    )
    assert len(preferential_rates) == 0

    data = {
        "commodity_codes": "1234567890\r\n2345678901\r\n12345678910",
        "duty_rate": "",
        "start_date_0": "",
        "start_date_1": "1",
        "start_date_2": "2023",
        "end_date_0": "31",
        "end_date_1": "12",
        "end_date_2": "2023",
    }
    create_url = reverse(
        "reference_documents:preferential_rates_bulk_create",
        kwargs={"pk": ref_doc_version.pk},
    )
    resp = client.post(create_url, data)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content.decode(resp.charset), "html.parser")
    error_messages = soup.select("ul.govuk-list.govuk-error-summary__list a")
    print(error_messages)
    assert "Duty rate is required" == error_messages[0].text
    assert "Enter the day, month and year" in error_messages[1].text
    assert (
        "Ensure all commodity codes are 10 digits and each on a new line"
        in error_messages[2].text
    )


@pytest.mark.reference_documents
def test_preferential_rate_bulk_create_without_permission(valid_user_client):
    """Test that posting the bulk create form without relevant user permissions
    does not work."""
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    data = {
        "commodity_codes": "1234567890\r\n2345678901\r\n3456789012\r\n4567890123",
        "duty_rate": "5%",
        "start_date_0": "1",
        "start_date_1": "1",
        "start_date_2": "2023",
        "end_date_0": "31",
        "end_date_1": "12",
        "end_date_2": "2023",
    }

    create_url = reverse(
        "reference_documents:preferential_rates_bulk_create",
        kwargs={"pk": ref_doc_version.pk},
    )
    resp = valid_user_client.post(create_url, data)
    assert resp.status_code == 403
    preferential_rates = PreferentialRate.objects.all().filter(
        reference_document_version=ref_doc_version,
    )
    assert len(preferential_rates) == 0
