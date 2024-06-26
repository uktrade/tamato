import pytest

from reference_documents.forms.reference_document_forms import (
    ReferenceDocumentCreateUpdateForm,
)
from reference_documents.forms.reference_document_forms import (
    ReferenceDocumentDeleteForm,
)
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
def test_ref_doc_create_update_form_valid_data():
    """Test that ReferenceDocumentCreateUpdateForm is valid when completed
    correctly."""
    data = {"title": "Reference document for XY", "area_id": "XY"}
    form = ReferenceDocumentCreateUpdateForm(data=data)

    assert form.is_valid()


@pytest.mark.reference_documents
def test_ref_doc_create_update_form_invalid_data():
    """Test that ReferenceDocumentCreateUpdateForm is invalid when not completed
    correctly."""
    form = ReferenceDocumentCreateUpdateForm(data={})
    assert not form.is_valid()
    assert "A reference document title is required" in form.errors["title"]
    assert "An area ID is required" in form.errors["area_id"]

    factories.ReferenceDocumentFactory.create(
        title="Reference document for XY",
        area_id="XY",
    )
    data = {"title": "Reference document for XY", "area_id": "VWXYZ"}
    form = ReferenceDocumentCreateUpdateForm(data=data)
    assert not form.is_valid()
    assert "Enter the area ID in the correct format" in form.errors["area_id"]
    assert "A reference document with this title already exists" in form.errors["title"]


@pytest.mark.reference_documents
def test_ref_doc_delete_form_valid():
    """Test that ReferenceDocumentDeleteForm is valid for a reference document
    with no versions."""
    ref_doc = factories.ReferenceDocumentFactory.create()
    form = ReferenceDocumentDeleteForm(data={}, instance=ref_doc)
    assert form.is_valid()


@pytest.mark.reference_documents
def test_ref_doc_delete_form_invalid():
    """Test that ReferenceDocumentDeleteForm is invalid for a reference document
    with versions."""
    ref_doc = factories.ReferenceDocumentFactory.create()
    factories.ReferenceDocumentVersionFactory(reference_document=ref_doc)
    form = ReferenceDocumentDeleteForm(data={}, instance=ref_doc)
    assert not form.is_valid()
