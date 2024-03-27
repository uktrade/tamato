import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.models import ReferenceDocument
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
def test_ref_doc_create_creates_object_and_redirects(valid_user, client):
    """Tests that posting the reference document create form adds the new
    reference document to the database and redirects to the confirm-create
    page."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="add_referencedocument"),
    )
    client.force_login(valid_user)
    create_url = reverse("reference_documents:create")
    form_data = {
        "title": "Reference document for XY",
        "area_id": "XY",
    }
    response = client.post(create_url, form_data)
    assert response.status_code == 302

    ref_doc = ReferenceDocument.objects.get(title=form_data["title"])
    assert ref_doc
    assert response.url == reverse(
        "reference_documents:confirm-create",
        kwargs={"pk": ref_doc.pk},
    )


@pytest.mark.reference_documents
def test_ref_doc_edit_updates_ref_doc_object(valid_user, client):
    """Tests that posting the reference document edit form updates the reference
    document and redirects to the confirm-update page."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="change_referencedocument"),
    )
    client.force_login(valid_user)

    ref_doc = factories.ReferenceDocumentFactory.create()

    edit_url = reverse(
        "reference_documents:edit",
        kwargs={"pk": ref_doc.pk},
    )

    new_title = "Updated title for this reference document"
    new_area_id = "XY"
    form_data = {
        "title": new_title,
        "area_id": new_area_id,
    }

    assert not ref_doc.title == new_title
    assert not ref_doc.area_id == new_area_id

    response = client.get(edit_url)
    assert response.status_code == 200

    response = client.post(edit_url, form_data)
    assert response.status_code == 302
    assert response.url == reverse(
        "reference_documents:confirm-update",
        kwargs={"pk": ref_doc.pk},
    )

    ref_doc.refresh_from_db()
    assert ref_doc.title == new_title
    assert ref_doc.area_id == new_area_id


@pytest.mark.reference_documents
def test_successfully_delete_ref_doc(valid_user, client):
    """Tests that posting the reference document delete form deletes the
    reference document and redirects to the confirm-delete page."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="delete_referencedocument"),
    )
    client.force_login(valid_user)

    ref_doc = factories.ReferenceDocumentFactory.create()
    assert ReferenceDocument.objects.filter(pk=ref_doc.pk)
    delete_url = reverse(
        "reference_documents:delete",
        kwargs={"pk": ref_doc.pk},
    )

    response = client.get(delete_url)
    page = BeautifulSoup(response.content, "html.parser")
    assert response.status_code == 200
    assert (
        f"Delete reference document {ref_doc.area_id}" in page.select("main h1")[0].text
    )

    response = client.post(delete_url)
    assert response.status_code == 302
    assert response.url == reverse(
        "reference_documents:confirm-delete",
        kwargs={"deleted_pk": ref_doc.pk},
    )
    assert not ReferenceDocument.objects.filter(pk=ref_doc.pk)


@pytest.mark.reference_documents
def test_delete_ref_doc_with_versions(valid_user, client):
    """Test that deleting a reference document with versions does not work."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="delete_referencedocument"),
    )
    client.force_login(valid_user)

    ref_doc = factories.ReferenceDocumentFactory.create()
    factories.ReferenceDocumentVersionFactory(reference_document=ref_doc)

    delete_url = reverse(
        "reference_documents:delete",
        kwargs={"pk": ref_doc.pk},
    )

    response = client.get(delete_url)
    assert response.status_code == 200

    response = client.post(delete_url)
    assert response.status_code == 200
    assert (
        f"Reference document {ref_doc.area_id} cannot be deleted as it has active versions."
        in str(response.content)
    )
    assert ReferenceDocument.objects.filter(pk=ref_doc.pk)


@pytest.mark.reference_documents
def test_ref_doc_crud_without_permission(valid_user_client):
    # TODO: potentially update this if the permissions for reference doc behaviour changes
    ref_doc = factories.ReferenceDocumentFactory.create()
    create_url = reverse("reference_documents:create")
    edit_url = reverse("reference_documents:edit", kwargs={"pk": ref_doc.pk})
    delete_url = reverse("reference_documents:delete", kwargs={"pk": ref_doc.pk})
    form_data = {
        "title": "Reference document for XY",
        "area_id": "XY",
    }
    response = valid_user_client.post(create_url, form_data)
    assert response.status_code == 403
    response = valid_user_client.post(edit_url, form_data)
    assert response.status_code == 403
    response = valid_user_client.post(delete_url)
    assert response.status_code == 403
