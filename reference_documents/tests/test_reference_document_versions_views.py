import datetime

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.urls import reverse

from common.tests.factories import QuotaOrderNumberFactory
from common.tests.factories import SimpleGoodsNomenclatureFactory
from common.tests.factories import date_ranges
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

    resp = client.get(create_url)
    assert resp.status_code == 200

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
    resp = client.post(create_url, form_data)
    assert resp.status_code == 302

    ref_doc = ReferenceDocumentVersion.objects.get(
        reference_document=ref_doc,
    )
    assert ref_doc
    assert resp.url == reverse(
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
    resp = client.get(edit_url)
    assert resp.status_code == 200
    assert ref_doc_version.version != 6.0

    resp = client.post(edit_url, form_data)
    assert resp.status_code == 302
    assert resp.url == reverse(
        "reference_documents:version-confirm-update",
        kwargs={"pk": ref_doc_version.pk},
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
    ref_doc = factories.ReferenceDocumentFactory.create(area_id="XY")
    ref_doc_version = factories.ReferenceDocumentVersionFactory.create(
        reference_document=ref_doc,
        version=3.0,
    )
    ref_doc_pk = ref_doc.pk
    area_id = ref_doc.area_id
    assert ReferenceDocumentVersion.objects.filter(pk=ref_doc_version.pk)
    delete_url = reverse(
        "reference_documents:version-delete",
        kwargs={"pk": ref_doc_version.pk, "ref_doc_pk": ref_doc_pk},
    )
    resp = client.get(delete_url)
    page = BeautifulSoup(resp.content, "html.parser")
    assert resp.status_code == 200
    assert (
        f"Delete reference document {area_id} version {ref_doc_version.version}"
        in page.select("main h1")[0].text
    )
    resp = client.post(delete_url)
    assert resp.status_code == 302
    assert resp.url == reverse(
        "reference_documents:version-confirm-delete",
        kwargs={"deleted_pk": ref_doc_version.pk},
    )
    assert not ReferenceDocumentVersion.objects.filter(pk=ref_doc_version.pk)
    resp = client.get(resp.url)
    assert (
        f"Reference document {area_id} version {ref_doc_version.version} has been deleted"
        in str(resp.content)
    )


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
    resp = client.get(delete_url)
    assert resp.status_code == 200

    resp = client.post(delete_url)
    assert resp.status_code == 200
    assert (
        f"Reference document version {ref_doc_version.version} cannot be deleted as it has current preferential duty rates or tariff quotas"
        in str(resp.content)
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
    resp = valid_user_client.post(create_url, form_data)
    assert resp.status_code == 403
    resp = valid_user_client.post(edit_url, form_data)
    assert resp.status_code == 403
    resp = valid_user_client.post(delete_url)
    assert resp.status_code == 403


@pytest.mark.skip(
    reason="FIXME: Random failure - https://uktrade.atlassian.net/browse/TP2000-1395",
)
@pytest.mark.reference_documents
def test_ref_doc_version_detail_view(superuser_client):
    """Test that the reference document version detail view shows preferential
    rate and tariff quota data."""
    ref_doc = factories.ReferenceDocumentFactory.create(
        area_id="XY",
        title="Reference document for XY",
    )
    ref_doc_version = factories.ReferenceDocumentVersionFactory(
        reference_document=ref_doc,
        version=1.0,
    )
    preferential_rate_batch = factories.PreferentialRateFactory.create_batch(
        10,
        reference_document_version=ref_doc_version,
    )
    first_preferential_rate = preferential_rate_batch[0]
    order_number_batch = factories.PreferentialQuotaOrderNumberFactory.create_batch(
        5,
        reference_document_version=ref_doc_version,
    )
    first_quota_order_number = order_number_batch[0].quota_order_number
    # Recreate the first quota and first preferential rate's commodity code in TAP
    tap_quota = QuotaOrderNumberFactory.create(order_number=first_quota_order_number)
    tap_commodity_code = SimpleGoodsNomenclatureFactory.create(
        item_id=first_preferential_rate.commodity_code,
        valid_between=date_ranges("big"),
        suffix=80,
    )
    core_data_tab = (
        reverse(
            "reference_documents:version-details",
            kwargs={"pk": ref_doc_version.pk},
        )
        + "#core-data"
    )
    response = superuser_client.get(core_data_tab)
    page = BeautifulSoup(response.content, "html.parser")
    assert response.status_code == 200
    # Assert the first rate's commodity code which exists in TAP appears as a link
    assert page.find("a", href=True, text=f"{first_preferential_rate.commodity_code}")
    table_rows = page.select("tr")
    # Assert there is a row for each preferential rate
    assert len(table_rows) == 11
    tariff_quotas_tab = (
        reverse(
            "reference_documents:version-details",
            kwargs={"pk": ref_doc_version.pk},
        )
        + "#tariff_quotas"
    )
    response = superuser_client.get(tariff_quotas_tab)
    page = BeautifulSoup(response.content, "html.parser")
    quota_link_header = page.select("h2 a")[0].get_text()
    # Assert the first quota which exists in TAP appears as a URL
    assert first_quota_order_number in quota_link_header
    assert response.status_code == 200
    # Assert the remaining four quotas appear too
    for order_number in order_number_batch[1:]:
        assert f"Order number {order_number.quota_order_number}" in str(
            response.content,
        )
