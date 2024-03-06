import pytest

from reference_documents import forms
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
def test_ref_doc_version_create_update_valid_data():
    """Test that ReferenceDocumentVersionCreateEditForm is valid when completed
    correctly."""
    ref_doc = factories.ReferenceDocumentFactory.create()
    data = {
        "reference_document": ref_doc,
        "version": "2.0",
        "published_date_0": "11",
        "published_date_1": "1",
        "published_date_2": "2024",
        "entry_into_force_date_0": "1",
        "entry_into_force_date_1": "1",
        "entry_into_force_date_2": "2024",
    }

    form = forms.ReferenceDocumentVersionsEditCreateForm(data=data)
    assert form.is_valid()


@pytest.mark.reference_documents
def test_ref_doc_version_create_update_invalid_data():
    """Test that ReferenceDocumentVersionCreateEditForm is invalid when not
    complete correctly."""
    form = forms.ReferenceDocumentVersionsEditCreateForm(data={})
    assert not form.is_valid()
    assert "A version number is required" in form.errors["version"]
    assert "A published date is required" in form.errors["published_date"]
    assert (
        "An entry into force date is required" in form.errors["entry_into_force_date"]
    )

    # Test that it fails if a version of a higher number already exists
    ref_doc = factories.ReferenceDocumentFactory.create()
    factories.ReferenceDocumentVersionFactory.create(
        reference_document=ref_doc,
        version=3.0,
    )
    data = {
        "reference_document": ref_doc,
        "version": "2.0",
        "published_date_0": "11",
        "published_date_1": "1",
        "published_date_2": "2024",
        "entry_into_force_date_0": "1",
        "entry_into_force_date_1": "1",
        "entry_into_force_date_2": "2024",
    }
    form = forms.ReferenceDocumentVersionsEditCreateForm(data=data)
    assert not form.is_valid()
    assert (
        "New versions of this reference document must be a higher number than previous versions"
        in form.errors["__all__"]
    )


@pytest.mark.reference_documents
def test_ref_doc_version_delete_valid():
    """Test that ReferenceDocumentVersionDeleteForm is valid for a reference
    document with no versions."""
    version = factories.ReferenceDocumentVersionFactory.create()
    form = forms.ReferenceDocumentVersionsEditCreateForm(data={}, instance=version)
    assert not form.is_valid()


@pytest.mark.reference_documents
def test_ref_doc_version_delete_invalid():
    """Test that ReferenceDocumentVersionDeleteForm is invalid for a reference
    document with versions."""
    version = factories.ReferenceDocumentVersionFactory.create()
    factories.PreferentialRateFactory.create(reference_document_version=version)
    form = forms.ReferenceDocumentVersionDeleteForm(data={}, instance=version)
    assert not form.is_valid()
    assert (
        f"Reference Document version {version.version} cannot be deleted as it has current preferential duty rates or tariff quotas"
        in form.errors["__all__"]
    )
