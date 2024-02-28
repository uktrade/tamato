import pytest

# from reference_documents.tests import factories
from reference_documents import forms

pytestmark = pytest.mark.django_db


def test_ref_doc_create_update_form_valid_data():
    """Test that ReferenceDocumentCreateUpdateForm is valid when completed
    correctly."""
    data = {"title": "Reference document for XY", "area_id": "XY"}
    form = forms.ReferenceDocumentCreateUpdateForm(data=data)

    assert form.is_valid()


def test_ref_doc_create_update_form_invalid_data():
    """Test that ReferenceDocumentCreateUpdateForm is invalid when not complete
    correctly."""
    form = forms.ReferenceDocumentCreateUpdateForm(data={})
    assert not form.is_valid()
    assert "A Reference Document title is required" in form.errors["title"]
    assert "An area ID is required" in form.errors["area_id"]

    # factories.ReferenceDocumentFactory.create(title="Reference document for XY", area_id="XY")
    data = {"title": "Reference document for XY", "area_id": "VWXYZ"}
    form = forms.ReferenceDocumentCreateUpdateForm(data=data)
    assert not form.is_valid()
    assert "The area ID must be 2 characters long" in form.errors["area_id"]
    assert "A Reference Document with this title already exists" in form.errors["title"]


def test_ref_doc_delete_form_valid():
    """Test that ReferenceDocumentDeleteForm is valid for a reference document
    with no versions."""


def test_ref_doc_delete_form_invalid():
    """Test that ReferenceDocumentDeleteForm is invalid for a reference document
    with versions."""
