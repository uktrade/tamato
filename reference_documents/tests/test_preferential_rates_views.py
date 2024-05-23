import pytest
from django.urls import reverse

from reference_documents.forms.preferential_rate_forms import (
    PreferentialRateCreateUpdateForm,
)
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
