import pytest

from reference_documents.forms.ref_rate_forms import RefRateBulkCreateForm
from reference_documents.forms.ref_rate_forms import RefRateCreateUpdateForm
from reference_documents.forms.ref_rate_forms import RefRateDeleteForm
from reference_documents.models import RefRate
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialRateCreateUpdateForm:
    def test_validation_valid(self):
        form = RefRateCreateUpdateForm(
            data={
                "commodity_code": "0100000000",
                "duty_rate": "10%",
                "start_date_0": "1",
                "start_date_1": "1",
                "start_date_2": "2024",
                "end_date": None,
            },
        )

        assert form.is_valid()

    def test_validation_no_comm_code(self):
        form = RefRateCreateUpdateForm(
            data={
                "commodity_code": "",
                "duty_rate": "",
                "start_date_0": "1",
                "start_date_1": "1",
                "start_date_2": "2024",
                "end_date": None,
            },
        )

        assert not form.is_valid()
        assert "commodity_code" in form.errors.as_data().keys()
        assert "duty_rate" in form.errors.as_data().keys()
        assert "start_date" not in form.errors.as_data().keys()
        assert "end_date" not in form.errors.as_data().keys()


@pytest.mark.reference_documents
class TestPreferentialRateDeleteForm:
    def test_init(self):
        ref_rate = factories.RefRateFactory()

        target = RefRateDeleteForm(
            instance=ref_rate,
        )

        assert target.instance == ref_rate
        assert target.Meta.fields == []
        assert target.Meta.model == RefRate


@pytest.mark.reference_documents
def test_preferential_rate_bulk_create_valid_data():
    """Test that preferential rate bulk create is valid when completed
    correctly."""
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    data = {
        "reference_document_version": ref_doc_version.pk,
        "commodity_codes": "1234567890\r\n2345678901",
        "duty_rate": "5%",
        "start_date_0": "1",
        "start_date_1": "1",
        "start_date_2": "2023",
        "end_date_0": "31",
        "end_date_1": "12",
        "end_date_2": "2023",
    }

    form = RefRateBulkCreateForm(
        data=data,
    )
    assert form.is_valid()


@pytest.mark.reference_documents
def test_preferential_rate_bulk_create_invalid_data():
    """Test that preferential rate bulk create is invalid when completed
    incorrectly."""
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    data = {
        "reference_document_version": ref_doc_version.pk,
        "commodity_codes": "1234567890\r\n2345678901\r\n12345678910",
        "duty_rate": "",
        "start_date_0": "1",
        "start_date_1": "1",
        "start_date_2": "2023",
        "end_date_0": "31",
        "end_date_1": "12",
        "end_date_2": "2022",
    }

    form = RefRateBulkCreateForm(
        data=data,
    )
    assert not form.is_valid()
    assert (
        "Ensure all commodity codes are 10 digits and each on a new line"
        in form.errors["commodity_codes"]
    )
    assert "Duty rate is required" in form.errors["duty_rate"]
    assert (
        "The end date must be the same as or after the start date."
        in form.errors["end_date"]
    )
