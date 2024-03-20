import pytest
from django.core.exceptions import ValidationError

from reference_documents.forms.preferential_quota_forms import (
    PreferentialQuotaBulkCreate,
)
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


@pytest.mark.reference_documents
def test_preferential_quota_bulk_create_valid_data():
    """Test that preferential quota bulk create is valid when completed
    correctly."""
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_quota_order_number = (
        factories.PreferentialQuotaOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
    )
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

    form = PreferentialQuotaBulkCreate(
        data=data,
        reference_document_version=ref_doc_version,
    )
    assert form.is_valid()


@pytest.mark.reference_documents
def test_preferential_quota_bulk_create_invalid_data():
    """Test that preferential quota bulk create is invalid when completed
    incorrectly."""
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    preferential_quota_order_number = (
        factories.PreferentialQuotaOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
    )
    data = {
        "preferential_quota_order_number": preferential_quota_order_number,
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

    form = PreferentialQuotaBulkCreate(
        data=data,
        reference_document_version=ref_doc_version,
    )
    assert not form.is_valid()
    assert (
        "Ensure all commodity codes are 10 digits and each on a new line"
        in form.errors["commodity_codes"]
    )
    assert "Duty rate is required" in form.errors["quota_duty_rate"]
    assert "Measurement is required" in form.errors["measurement"]
    assert (
        "The end date must be the same as or after the start date."
        in form.errors["end_date_1"]
    )
    assert "Enter the day, month and year" in form.errors["start_date_2"]
