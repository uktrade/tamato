from datetime import date

import pytest
from django.core.exceptions import ValidationError

from common.util import TaricDateRange
from reference_documents.forms.ref_quota_definition_forms import (
    RefQuotaDefinitionBulkCreateForm,
)
from reference_documents.forms.ref_quota_definition_forms import (
    RefQuotaDefinitionCreateUpdateForm,
)
from reference_documents.forms.ref_quota_definition_forms import (
    RefQuotaDefinitionDeleteForm,
)
from reference_documents.models import RefQuotaDefinition
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaCreateUpdateForm:
    def test_init(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        target = RefQuotaDefinitionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            ref_quota_definition.ref_order_number,
            instance=ref_quota_definition,
        )

        # it sets initial values
        assert (
            target.initial["ref_order_number"] == ref_quota_definition.ref_order_number
        )
        assert (
            target.reference_document_version
            == ref_quota_definition.ref_order_number.reference_document_version
        )
        assert target.Meta.fields == [
            "ref_order_number",
            "commodity_code",
            "duty_rate",
            "volume",
            "measurement",
            "valid_between",
        ]

    def test_clean_duty_rate_pass(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        data = {
            "duty_rate": "10%",
        }

        target = RefQuotaDefinitionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            ref_quota_definition.ref_order_number,
            instance=ref_quota_definition,
            data=data,
        )

        assert not target.is_valid()
        assert target.clean_duty_rate() == "10%"

    def test_clean_duty_rate_fail(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        data = {
            "duty_rate": "",
        }

        target = RefQuotaDefinitionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            ref_quota_definition.ref_order_number,
            instance=ref_quota_definition,
            data=data,
        )

        assert not target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean_duty_rate()

        assert "Duty Rate is not valid - it must have a value" in str(ve)

    def test_clean_ref_order_number_pass(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        data = {
            "ref_order_number": ref_quota_definition.ref_order_number.pk,
        }

        target = RefQuotaDefinitionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            ref_quota_definition.ref_order_number,
            instance=ref_quota_definition,
            data=data,
        )

        assert not target.is_valid()

        assert target.clean_ref_order_number() is not None

    def test_ref_order_number_fail(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        data = {
            "ref_order_number": None,
        }

        target = RefQuotaDefinitionCreateUpdateForm(
            ref_quota_definition.ref_order_number.reference_document_version,
            ref_quota_definition.ref_order_number,
            instance=ref_quota_definition,
            data=data,
        )

        assert not target.is_valid()

        with pytest.raises(ValidationError) as ve:
            target.clean_ref_order_number()

        assert "Quota order number is required" in str(ve)


@pytest.mark.reference_documents
class TestPreferentialQuotaDeleteForm:
    def test_init(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory()

        target = RefQuotaDefinitionDeleteForm(
            instance=ref_quota_definition,
        )

        assert target.instance == ref_quota_definition
        assert target.Meta.fields == []
        assert target.Meta.model == RefQuotaDefinition


@pytest.mark.reference_documents
class TestRefQuotaDefinitionBulkCreateForm:

    def test_preferential_quota_bulk_create_valid_data(self):
        """Test that preferential quota bulk create is valid when completed
        correctly."""
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
        ref_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
        data = {
            "ref_order_number": ref_order_number.pk,
            "commodity_codes": "1234567890\r\n2345678901",
            "duty_rate": "5%",
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

        form = RefQuotaDefinitionBulkCreateForm(
            data=data,
            reference_document_version=ref_doc_version,
        )
        assert form.is_valid()

    def test_preferential_quota_bulk_create_invalid_data(self):
        """Test that preferential quota bulk create is invalid when completed
        incorrectly."""
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
        ref_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
        data = {
            "ref_order_number": ref_order_number,
            "commodity_codes": "1234567890\r\n2345678901\r\n12345678910",
            "duty_rate": "",
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

        form = RefQuotaDefinitionBulkCreateForm(
            data=data,
            reference_document_version=ref_doc_version,
        )
        assert not form.is_valid()
        assert (
            "Ensure all commodity codes are 10 digits and each on a new line"
            in form.errors["commodity_codes"]
        )
        assert "Duty rate is required" in form.errors["duty_rate"]
        assert "Measurement is required" in form.errors["measurement"]
        assert (
            "The end date must be the same as or after the start date."
            in form.errors["end_date_1"]
        )
        assert "Enter the day, month and year" in form.errors["start_date_2"]

    def test_preferential_quota_bulk_create_invalid_start_end_date(self):
        """Test that preferential quota bulk create is invalid when completed
        incorrectly."""
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
        ref_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
        data = {
            "ref_order_number": ref_order_number,
            "commodity_codes": "1234567890\r\n2345678901\r\n12345678910",
            "duty_rate": "",
            "measurement": "",
            "start_date_0_0": "1",
            "start_date_0_1": "11",
            "start_date_0_2": "2023",
            "end_date_0_0": "1",
            "end_date_0_1": "10",
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

        form = RefQuotaDefinitionBulkCreateForm(
            data=data,
            reference_document_version=ref_doc_version,
            initial={
                "valid_between_0": TaricDateRange(date(1999, 1, 1), date(1999, 2, 1)),
            },
        )
        assert not form.is_valid()
        assert (
            "Ensure all commodity codes are 10 digits and each on a new line"
            in form.errors["commodity_codes"]
        )
        assert "Duty rate is required" in form.errors["duty_rate"]
        assert "Measurement is required" in form.errors["measurement"]
        assert (
            "The end date must be the same as or after the start date."
            in form.errors["end_date_1"]
        )
        assert "Enter the day, month and year" in form.errors["start_date_2"]
