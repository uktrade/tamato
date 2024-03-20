import pytest
from django.core.exceptions import ValidationError

from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaCreateUpdateForm,
)
from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaDeleteForm,
)
from reference_documents.models import PreferentialQuota
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaCreateUpdateForm:
    def test_init(self):
        pref_quota = factories.PreferentialQuotaFactory()

        target = PreferentialQuotaCreateUpdateForm(
            pref_quota.preferential_quota_order_number.reference_document_version,
            pref_quota.preferential_quota_order_number,
            instance=pref_quota,
        )

        # it sets initial values
        assert (
            target.initial["preferential_quota_order_number"]
            == pref_quota.preferential_quota_order_number
        )
        assert (
            target.reference_document_version
            == pref_quota.preferential_quota_order_number.reference_document_version
        )
        assert target.Meta.fields == [
            "preferential_quota_order_number",
            "commodity_code",
            "quota_duty_rate",
            "volume",
            "measurement",
            "valid_between",
        ]

    def test_clean_quota_duty_rate_pass(self):
        pref_quota = factories.PreferentialQuotaFactory()

        data = {
            "quota_duty_rate": "10%",
        }

        target = PreferentialQuotaCreateUpdateForm(
            pref_quota.preferential_quota_order_number.reference_document_version,
            pref_quota.preferential_quota_order_number,
            instance=pref_quota,
            data=data,
        )

        assert not target.is_valid()
        assert target.clean_quota_duty_rate() == "10%"

    def test_clean_quota_duty_rate_fail(self):
        pref_quota = factories.PreferentialQuotaFactory()

        data = {
            "quota_duty_rate": "",
        }

        target = PreferentialQuotaCreateUpdateForm(
            pref_quota.preferential_quota_order_number.reference_document_version,
            pref_quota.preferential_quota_order_number,
            instance=pref_quota,
            data=data,
        )

        assert not target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean_quota_duty_rate()

        assert "Quota duty Rate is not valid - it must have a value" in str(ve)

    def test_clean_preferential_quota_order_number_pass(self):
        pref_quota = factories.PreferentialQuotaFactory()

        data = {
            "preferential_quota_order_number": pref_quota.preferential_quota_order_number.pk,
        }

        target = PreferentialQuotaCreateUpdateForm(
            pref_quota.preferential_quota_order_number.reference_document_version,
            pref_quota.preferential_quota_order_number,
            instance=pref_quota,
            data=data,
        )

        assert not target.is_valid()

        assert target.clean_preferential_quota_order_number() is not None

    def test_preferential_quota_order_number_fail(self):
        pref_quota = factories.PreferentialQuotaFactory()

        data = {
            "preferential_quota_order_number": None,
        }

        target = PreferentialQuotaCreateUpdateForm(
            pref_quota.preferential_quota_order_number.reference_document_version,
            pref_quota.preferential_quota_order_number,
            instance=pref_quota,
            data=data,
        )

        assert not target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean_preferential_quota_order_number()

        assert "Quota Order Number is not valid - it must have a value" in str(ve)


@pytest.mark.reference_documents
class TestPreferentialQuotaDeleteForm:
    def test_init(self):
        pref_quota = factories.PreferentialQuotaFactory()

        target = PreferentialQuotaDeleteForm(
            instance=pref_quota,
        )

        assert target.instance == pref_quota
        assert target.Meta.fields == []
        assert target.Meta.model == PreferentialQuota
