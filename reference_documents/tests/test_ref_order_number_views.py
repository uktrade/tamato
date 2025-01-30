from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from reference_documents.models import RefOrderNumber
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumberEditView:
    def test_get_without_permissions(self, valid_user_client):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        resp = valid_user_client.get(
            reverse(
                "reference_documents:order-number-edit",
                kwargs={"pk": pref_quota_order_number.pk},
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        pref_quota_order_number = factories.RefOrderNumberFactory()

        resp = superuser_client.get(
            reverse(
                "reference_documents:order-number-edit",
                kwargs={"pk": pref_quota_order_number.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post_with_permission_pass_not_sub_quota(self, superuser_client):
        pref_quota_order_number = factories.RefOrderNumberFactory.create()

        post_data = {
            "order_number": "054321",
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2022,
            "end_date_0": 1,
            "end_date_1": 1,
            "end_date_2": 2023,
            "coefficient": "",
            "main_order_number": "",
            "reference_document_version_id": pref_quota_order_number.reference_document_version.pk,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:order-number-edit",
                kwargs={"pk": pref_quota_order_number.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302

        pref_quota_order_number.refresh_from_db()

        # check the update was applied
        assert pref_quota_order_number.valid_between.lower == date(2022, 1, 1)
        assert pref_quota_order_number.valid_between.upper == date(2023, 1, 1)
        assert pref_quota_order_number.coefficient is None
        assert pref_quota_order_number.order_number == "054321"
        assert pref_quota_order_number.main_order_number_id is None

    def test_post_with_permission_pass_with_sub_quota(self, superuser_client):
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
        pref_quota_order_number_main = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )
        pref_quota_order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )

        post_data = {
            "order_number": "054321",
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2022,
            "end_date_0": 1,
            "end_date_1": 1,
            "end_date_2": 2023,
            "coefficient": "1.2",
            "relation_type": "EQ",
            "main_order_number": pref_quota_order_number_main.pk,
            "reference_document_version_id": pref_quota_order_number_main.reference_document_version.pk,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:order-number-edit",
                kwargs={"pk": pref_quota_order_number.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302

        pref_quota_order_number.refresh_from_db()

        # check the update was applied
        assert pref_quota_order_number.valid_between.lower == date(2022, 1, 1)
        assert pref_quota_order_number.valid_between.upper == date(2023, 1, 1)
        assert pref_quota_order_number.coefficient == Decimal("1.2")
        assert pref_quota_order_number.order_number == "054321"
        assert pref_quota_order_number.relation_type == "EQ"
        assert pref_quota_order_number.main_order_number == pref_quota_order_number_main


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumberCreateView:
    def test_get_without_permissions(self, valid_user_client):
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()

        resp = valid_user_client.get(
            reverse(
                "reference_documents:order-number-create",
                kwargs={"pk": ref_doc_version.pk},
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()

        resp = superuser_client.get(
            reverse(
                "reference_documents:order-number-create",
                kwargs={"pk": ref_doc_version.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post_with_permission_pass_not_sub_quota(self, superuser_client):
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()

        post_data = {
            "order_number": "054321",
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2022,
            "end_date_0": 1,
            "end_date_1": 1,
            "end_date_2": 2023,
            "coefficient": "",
            "main_order_number": "",
            "relation_type": "",
            "reference_document_version_id": ref_doc_version.pk,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:order-number-create",
                kwargs={"pk": ref_doc_version.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302

        pref_quota_order_number = ref_doc_version.ref_order_numbers.all().last()

        # check the update was applied
        assert pref_quota_order_number.valid_between.lower == date(2022, 1, 1)
        assert pref_quota_order_number.valid_between.upper == date(2023, 1, 1)
        assert pref_quota_order_number.coefficient is None
        assert pref_quota_order_number.order_number == "054321"
        assert pref_quota_order_number.main_order_number is None
        assert pref_quota_order_number.relation_type == ""

    def test_post_with_permission_pass_with_sub_quota(self, superuser_client):
        ref_doc_version = factories.ReferenceDocumentVersionFactory.create()
        pref_quota_order_number_main = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_version,
        )

        post_data = {
            "order_number": "054321",
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2022,
            "end_date_0": 1,
            "end_date_1": 1,
            "end_date_2": 2023,
            "coefficient": "1.2",
            "main_order_number": pref_quota_order_number_main.pk,
            "relation_type": "EQ",
            "reference_document_version_id": ref_doc_version.pk,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:order-number-create",
                kwargs={"pk": ref_doc_version.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302

        pref_quota_order_number = ref_doc_version.ref_order_numbers.all().last()

        # check the update was applied
        assert pref_quota_order_number.valid_between.lower == date(2022, 1, 1)
        assert pref_quota_order_number.valid_between.upper == date(2023, 1, 1)
        assert pref_quota_order_number.coefficient == Decimal("1.2")
        assert pref_quota_order_number.order_number == "054321"
        assert pref_quota_order_number.main_order_number == pref_quota_order_number_main
        assert pref_quota_order_number.relation_type == "EQ"


@pytest.mark.reference_documents
class TestPreferentialQuotaOrderNumberDeleteView:
    def test_get_without_permissions(self, valid_user_client):
        pref_quota_order_number = factories.RefOrderNumberFactory.create()
        ref_doc_version = pref_quota_order_number.reference_document_version

        resp = valid_user_client.get(
            reverse(
                "reference_documents:order-number-delete",
                kwargs={
                    "pk": pref_quota_order_number.pk,
                    "version_pk": ref_doc_version.pk,
                },
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        pref_quota_order_number = factories.RefOrderNumberFactory.create()
        ref_doc_version = pref_quota_order_number.reference_document_version

        resp = superuser_client.get(
            reverse(
                "reference_documents:order-number-delete",
                kwargs={
                    "pk": pref_quota_order_number.pk,
                    "version_pk": ref_doc_version.pk,
                },
            ),
        )

        assert resp.status_code == 200

    def test_post_with_permission(self, superuser_client):
        pref_quota_order_number = factories.RefOrderNumberFactory.create()
        ref_doc_version = pref_quota_order_number.reference_document_version
        pref_quota_order_number_id = pref_quota_order_number.id
        resp = superuser_client.post(
            reverse(
                "reference_documents:order-number-delete",
                kwargs={
                    "pk": pref_quota_order_number.pk,
                    "version_pk": ref_doc_version.pk,
                },
            ),
            {},
        )

        assert resp.status_code == 302
        results = RefOrderNumber.objects.all().filter(
            id=pref_quota_order_number_id,
        )
        assert len(results) == 0

    def test_post_without_permission(self, valid_user_client):
        pref_quota_order_number = factories.RefOrderNumberFactory.create()
        ref_doc_version = pref_quota_order_number.reference_document_version
        pref_quota_order_number_id = pref_quota_order_number.id
        resp = valid_user_client.post(
            reverse(
                "reference_documents:order-number-delete",
                kwargs={
                    "pk": pref_quota_order_number.pk,
                    "version_pk": ref_doc_version.pk,
                },
            ),
            {},
        )

        assert resp.status_code == 403
        results = RefOrderNumber.objects.all().filter(
            id=pref_quota_order_number_id,
        )
        assert len(results) == 1

    def test_post_with_permission_with_sub_records(self, superuser_client):
        pref_quota_order_number = (
            factories.RefQuotaDefinitionFactory.create().ref_order_number
        )
        ref_doc_version = pref_quota_order_number.reference_document_version
        pref_quota_order_number_id = pref_quota_order_number.id

        resp = superuser_client.post(
            reverse(
                "reference_documents:order-number-delete",
                kwargs={
                    "pk": pref_quota_order_number.pk,
                    "version_pk": ref_doc_version.pk,
                },
            ),
            {},
        )

        assert resp.status_code == 200
        results = RefOrderNumber.objects.all().filter(
            id=pref_quota_order_number_id,
        )
        assert len(results) == 1
