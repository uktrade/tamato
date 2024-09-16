from datetime import date

import pytest
from django.urls import reverse

from common.util import TaricDateRange
from reference_documents.models import ReferenceDocumentVersionStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaSuspensionRangeEdit:
    def test_get(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(
            status=ReferenceDocumentVersionStatus.EDITING,
        )
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
        )
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory(
            ref_order_number=ref_order_number,
        )
        ref_quota_suspension_range = factories.RefQuotaSuspensionRangeFactory(
            ref_quota_definition_range=ref_quota_definition_range,
        )

        resp = superuser_client.get(
            reverse(
                "reference_documents:quota-suspension-range-edit",
                kwargs={"pk": ref_quota_suspension_range.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(
            status=ReferenceDocumentVersionStatus.EDITING,
        )
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
            valid_between=TaricDateRange(date(2020, 1, 1)),
        )
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory(
            ref_order_number=ref_order_number,
        )
        ref_quota_suspension_range = factories.RefQuotaSuspensionRangeFactory(
            ref_quota_definition_range=ref_quota_definition_range,
        )

        post_data = {
            "ref_quota_definition_range": ref_quota_definition_range.pk,
            "start_year": 2020,
            "start_month": 1,
            "start_day": 1,
            "end_year": 2022,
            "end_month": 2,
            "end_day": 1,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:quota-suspension-range-edit",
                kwargs={"pk": ref_quota_suspension_range.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302


@pytest.mark.reference_documents
class TestRefQuotaSuspensionRangeCreate:
    def test_get(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(
            status=ReferenceDocumentVersionStatus.EDITING,
        )

        resp = superuser_client.get(
            reverse(
                "reference_documents:quota-suspension-range-create",
                kwargs={"version_pk": ref_doc_ver.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(
            status=ReferenceDocumentVersionStatus.EDITING,
        )
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
            valid_between=TaricDateRange(date(2020, 1, 1)),
        )
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory(
            ref_order_number=ref_order_number,
        )

        post_data = {
            "start_year": 2020,
            "start_month": 1,
            "start_day": 1,
            "end_year": 2022,
            "end_month": 2,
            "end_day": 1,
            "ref_quota_definition_range": ref_quota_definition_range.id,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:quota-suspension-range-create",
                kwargs={"version_pk": ref_doc_ver.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302


@pytest.mark.reference_documents
class TestRefQuotaSuspensionRangeDelete:
    def test_get(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(
            status=ReferenceDocumentVersionStatus.EDITING,
        )
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
        )
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory(
            ref_order_number=ref_order_number,
        )
        ref_quota_suspension_range = factories.RefQuotaSuspensionRangeFactory(
            ref_quota_definition_range=ref_quota_definition_range,
        )

        resp = superuser_client.get(
            reverse(
                "reference_documents:quota-suspension-range-delete",
                kwargs={
                    "pk": ref_quota_suspension_range.pk,
                    "version_pk": ref_doc_ver.pk,
                },
            ),
        )
        assert resp.status_code == 200

    def test_post(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(
            status=ReferenceDocumentVersionStatus.EDITING,
        )
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
        )
        ref_quota_definition_range = factories.RefQuotaDefinitionRangeFactory(
            ref_order_number=ref_order_number,
        )
        ref_quota_suspension_range = factories.RefQuotaSuspensionRangeFactory(
            ref_quota_definition_range=ref_quota_definition_range,
        )

        resp = superuser_client.post(
            reverse(
                "reference_documents:quota-suspension-range-delete",
                kwargs={
                    "pk": ref_quota_suspension_range.pk,
                    "version_pk": ref_doc_ver.pk,
                },
            ),
        )

        assert resp.status_code == 302
