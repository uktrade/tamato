from datetime import date

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import Permission
from django.urls import reverse

from common.util import TaricDateRange
from reference_documents.models import RefQuotaDefinition, ReferenceDocumentVersionStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaSuspensionEdit:
    def test_get(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(status=ReferenceDocumentVersionStatus.EDITING)
        ref_order_number = factories.RefOrderNumberFactory(reference_document_version=ref_doc_ver)
        ref_quota_definition = factories.RefQuotaDefinitionFactory(ref_order_number=ref_order_number)
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(ref_quota_definition=ref_quota_definition)

        resp = superuser_client.get(
            reverse(
                "reference_documents:quota-suspension-edit",
                kwargs={"pk": ref_quota_suspension.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(status=ReferenceDocumentVersionStatus.EDITING)
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
            valid_between=TaricDateRange(date(2020, 1, 1))
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory(
            ref_order_number=ref_order_number,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        )
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            ref_quota_definition=ref_quota_definition,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 2, 1))
                                                                          )

        post_data = {
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2020,
            "end_date_0": 2,
            "end_date_1": 3,
            "end_date_2": 2020,
            'ref_quota_definition': ref_quota_definition.id
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:quota-suspension-edit",
                kwargs={"pk": ref_quota_suspension.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302

@pytest.mark.reference_documents
class TestRefQuotaSuspensionCreate:
    def test_get(self, superuser_client):

        ref_doc_ver = factories.ReferenceDocumentVersionFactory(status=ReferenceDocumentVersionStatus.EDITING)
        ref_order_number = factories.RefOrderNumberFactory(reference_document_version=ref_doc_ver)

        resp = superuser_client.get(
            reverse(
                "reference_documents:quota-suspension-create",
                kwargs={"pk": ref_doc_ver.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(status=ReferenceDocumentVersionStatus.EDITING)
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
            valid_between=TaricDateRange(date(2020, 1, 1))
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory(
            ref_order_number=ref_order_number,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        )
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            ref_quota_definition=ref_quota_definition,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 2, 1))
        )

        post_data = {
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2020,
            "end_date_0": 2,
            "end_date_1": 3,
            "end_date_2": 2020,
            'ref_quota_definition': ref_quota_definition.id
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:quota-suspension-create",
                kwargs={"pk": ref_doc_ver.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302


@pytest.mark.reference_documents
class TestRefQuotaSuspensionDelete:
    def test_get(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(status=ReferenceDocumentVersionStatus.EDITING)
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
            valid_between=TaricDateRange(date(2020, 1, 1))
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory(
            ref_order_number=ref_order_number,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        )
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            ref_quota_definition=ref_quota_definition,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 2, 1))
        )

        resp = superuser_client.get(
            reverse(
                "reference_documents:quota-suspension-delete",
                kwargs={"pk": ref_quota_suspension.pk, 'version_pk': ref_doc_ver.pk},
            ),
        )
        assert resp.status_code == 200

    def test_post(self, superuser_client):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory(status=ReferenceDocumentVersionStatus.EDITING)
        ref_order_number = factories.RefOrderNumberFactory(
            reference_document_version=ref_doc_ver,
            valid_between=TaricDateRange(date(2020, 1, 1))
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory(
            ref_order_number=ref_order_number,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        )
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            ref_quota_definition=ref_quota_definition,
            valid_between=TaricDateRange(date(2020, 1, 1), date(2020, 2, 1))
        )

        post_data = {
            "start_date_0": 1,
            "start_date_1": 1,
            "start_date_2": 2020,
            "end_date_0": 2,
            "end_date_1": 3,
            "end_date_2": 2020,
            'ref_quota_definition': ref_quota_definition.id
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:quota-suspension-delete",
                kwargs={"pk": ref_quota_suspension.pk, 'version_pk': ref_doc_ver.pk},
            ),
            post_data,
        )

        assert resp.status_code == 302