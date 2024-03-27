import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.forms.preferential_rate_forms import (
    PreferentialRateCreateUpdateForm,
)
from reference_documents.tests import factories
from reference_documents.views.preferential_rate_views import PreferentialRateEdit

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
class TestPreferentialRateDeleteView:
    pass
