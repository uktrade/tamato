import datetime

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.urls import reverse

from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
def test_ref_doc_version_create_creates_object_and_redirects(valid_user, client):
    """Tests that posting the reference document version create form adds the
    new version to the database and redirects to the confirm-create page."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="add_referencedocumentversion"),
    )
    client.force_login(valid_user)
    ref_doc = factories.ReferenceDocumentFactory.create()

    create_url = reverse(
        "reference_documents:version-create",
        kwargs={"pk": ref_doc.pk},
    )
    form_data = {
        "reference_document": ref_doc.pk,
        "version": "2.0",
        "published_date_0": "11",
        "published_date_1": "1",
        "published_date_2": "2024",
        "entry_into_force_date_0": "1",
        "entry_into_force_date_1": "1",
        "entry_into_force_date_2": "2024",
    }
    response = client.post(create_url, form_data)
    assert response.status_code == 302

    ref_doc = ReferenceDocumentVersion.objects.get(
        reference_document=form_data["reference_document"],
    )
    assert ref_doc
    assert response.url == reverse(
        "reference_documents:version-confirm-create",
        kwargs={"pk": ref_doc.pk},
    )


@pytest.mark.reference_documents
def test_ref_doc_version_edit_updates_ref_doc_object(client, valid_user):
    """Tests that posting the reference document version edit form updates the
    reference document and redirects to the confirm-update page."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="change_referencedocumentversion"),
    )
    client.force_login(valid_user)
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()

    edit_url = reverse(
        "reference_documents:version-edit",
        kwargs={
            "pk": ref_doc_version.pk,
            "ref_doc_pk": ref_doc_version.reference_document.pk,
        },
    )
    form_data = {
        "reference_document": ref_doc_version.reference_document.pk,
        "version": "6.0",
        "published_date_0": "1",
        "published_date_1": "1",
        "published_date_2": "2024",
        "entry_into_force_date_0": "1",
        "entry_into_force_date_1": "1",
        "entry_into_force_date_2": "2024",
    }
    response = client.get(edit_url)
    assert response.status_code == 200
    assert ref_doc_version.version != 6.0

    response = client.post(edit_url, form_data)
    assert response.status_code == 302
    assert response.url == reverse(
        "reference_documents:version-confirm-update",
        kwargs={"pk": ref_doc_version.reference_document.pk},
    )
    ref_doc_version.refresh_from_db()
    assert ref_doc_version.version == 6.0
    assert ref_doc_version.published_date == datetime.date(2024, 1, 1)
    assert ref_doc_version.entry_into_force_date == datetime.date(2024, 1, 1)


@pytest.mark.reference_documents
def test_successfully_delete_ref_doc_version(valid_user, client):
    """Tests that posting the reference document version delete form deletes the
    reference document and redirects to the confirm-delete page."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="delete_referencedocumentversion"),
    )
    client.force_login(valid_user)
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    ref_doc_pk = ref_doc_version.reference_document.pk
    area_id = ref_doc_version.reference_document.area_id
    assert ReferenceDocumentVersion.objects.filter(pk=ref_doc_version.pk)
    delete_url = reverse(
        "reference_documents:version-delete",
        kwargs={"pk": ref_doc_version.pk, "ref_doc_pk": ref_doc_pk},
    )
    response = client.get(delete_url)
    page = BeautifulSoup(response.content, "html.parser")
    assert response.status_code == 200
    assert (
        f"Delete Reference Document {area_id} version {ref_doc_version.version}"
        in page.select("main h1")[0].text
    )
    response = client.post(delete_url)
    assert response.status_code == 302
    assert response.url == reverse(
        "reference_documents:version-confirm-delete",
        kwargs={"deleted_pk": ref_doc_version.pk},
    )
    assert not ReferenceDocumentVersion.objects.filter(pk=ref_doc_version.pk)


@pytest.mark.reference_documents
def test_delete_ref_doc_version_invalid(valid_user, client):
    """Test that deleting a reference document version with preferential rates
    does not work."""
    valid_user.user_permissions.add(
        Permission.objects.get(codename="delete_referencedocumentversion"),
    )
    client.force_login(valid_user)

    preferential_rate = factories.PreferentialRateFactory.create()
    ref_doc_version = preferential_rate.reference_document_version
    ref_doc = ref_doc_version.reference_document

    delete_url = reverse(
        "reference_documents:version-delete",
        kwargs={"pk": ref_doc_version.pk, "ref_doc_pk": ref_doc.pk},
    )
    response = client.get(delete_url)
    assert response.status_code == 200

    response = client.post(delete_url)
    assert response.status_code == 200
    assert (
        f"Reference Document version {ref_doc_version.version} cannot be deleted as it has current preferential duty rates or tariff quotas"
        in str(response.content)
    )
    assert ReferenceDocument.objects.filter(pk=ref_doc.pk)


@pytest.mark.reference_documents
def test_ref_doc_crud_without_permission(valid_user_client):
    # TODO: potentially update this if the permissions for reference doc behaviour changes
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
    ref_doc = ref_doc_version.reference_document
    create_url = reverse(
        "reference_documents:version-create",
        kwargs={"pk": ref_doc_version.pk},
    )
    edit_url = reverse(
        "reference_documents:version-edit",
        kwargs={"pk": ref_doc_version.pk, "ref_doc_pk": ref_doc.pk},
    )
    delete_url = reverse(
        "reference_documents:version-delete",
        kwargs={"pk": ref_doc_version.pk, "ref_doc_pk": ref_doc.pk},
    )
    form_data = {
        "reference_document": ref_doc.pk,
        "version": "2.0",
        "published_date_0": "11",
        "published_date_1": "1",
        "published_date_2": "2024",
        "entry_into_force_date_0": "1",
        "entry_into_force_date_1": "1",
        "entry_into_force_date_2": "2024",
    }
    response = valid_user_client.post(create_url, form_data)
    assert response.status_code == 403
    response = valid_user_client.post(edit_url, form_data)
    assert response.status_code == 403
    response = valid_user_client.post(delete_url)
    assert response.status_code == 403
