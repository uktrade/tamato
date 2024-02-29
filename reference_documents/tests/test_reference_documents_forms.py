import pytest

from reference_documents import forms
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
def test_ref_doc_create_update_form_valid_data():
    """Test that ReferenceDocumentCreateUpdateForm is valid when completed
    correctly."""
    data = {"title": "Reference document for XY", "area_id": "XY"}
    form = forms.ReferenceDocumentCreateUpdateForm(data=data)

    assert form.is_valid()


@pytest.mark.reference_documents
def test_ref_doc_create_update_form_invalid_data():
    """Test that ReferenceDocumentCreateUpdateForm is invalid when not complete
    correctly."""
    form = forms.ReferenceDocumentCreateUpdateForm(data={})
    assert not form.is_valid()
    assert "A Reference Document title is required" in form.errors["title"]
    assert "An area ID is required" in form.errors["area_id"]

    factories.ReferenceDocumentFactory.create(
        title="Reference document for XY",
        area_id="XY",
    )
    data = {"title": "Reference document for XY", "area_id": "VWXYZ"}
    form = forms.ReferenceDocumentCreateUpdateForm(data=data)
    assert not form.is_valid()
    assert "The area ID can be at most 4 characters long" in form.errors["area_id"]
    assert "A Reference Document with this title already exists" in form.errors["title"]


@pytest.mark.reference_documents
def test_ref_doc_delete_form_valid():
    """Test that ReferenceDocumentDeleteForm is valid for a reference document
    with no versions."""
    ref_doc = factories.ReferenceDocumentFactory.create(
        title="Reference document for XY",
        area_id="XY",
    )
    form = forms.ReferenceDocumentDeleteForm(data={}, instance=ref_doc)
    assert form.is_valid()


@pytest.mark.reference_documents
def test_ref_doc_delete_form_invalid():
    """Test that ReferenceDocumentDeleteForm is invalid for a reference document
    with versions."""
    ref_doc = factories.ReferenceDocumentFactory.create(
        title="Reference document for XY",
        area_id="XY",
    )
    factories.ReferenceDocumentVersionFactory(reference_document=ref_doc)
    form = forms.ReferenceDocumentDeleteForm(data={}, instance=ref_doc)
    assert not form.is_valid()
