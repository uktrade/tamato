import os
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from reference_documents.tests import factories
from reference_documents.tests.factories import CSVUploadFactory

pytestmark = pytest.mark.django_db

def open_support_file(file_name, from_file):
    path_to_current_file = os.path.realpath(from_file)
    current_directory = os.path.split(path_to_current_file)[0]
    return open(os.path.join(current_directory, "support", file_name), 'r')

@pytest.mark.reference_documents
class TestReferenceDocumentCsvUploadList:
    def test_get_without_permissions(self, valid_user_client):
        resp = valid_user_client.get(
            reverse(
                "reference_documents:reference-document-csv-index"
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        resp = superuser_client.get(
            reverse(
                "reference_documents:reference-document-csv-index"
            ),
        )
        assert resp.status_code == 200

@pytest.mark.reference_documents
class TestReferenceDocumentCsvUploadDetails:
    def test_get_without_permissions(self, valid_user_client):
        csv_upload = CSVUploadFactory.create()

        resp = valid_user_client.get(
            reverse(
                "reference_documents:reference-document-csv-upload-details",
                kwargs={'pk': csv_upload.pk}
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        csv_upload = CSVUploadFactory.create()

        resp = superuser_client.get(
            reverse(
                "reference_documents:reference-document-csv-upload-details",
                kwargs={'pk': csv_upload.pk}
            ),
        )
        assert resp.status_code == 200

@pytest.mark.reference_documents
class TestReferenceDocumentCsvUploadCreate:
    def test_get_without_permissions(self, valid_user_client):
        resp = valid_user_client.get(
            reverse(
                "reference_documents:reference-document-csv-upload"
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        resp = superuser_client.get(
            reverse(
                "reference_documents:reference-document-csv-upload"
            ),
        )
        assert resp.status_code == 200
    def test_post_without_permissions(self, valid_user_client):
        preferential_rates_csv_file = open_support_file('test_preferential_rates.csv', __file__)
        order_number_csv_file = open_support_file('test_order_numbers.csv', __file__)
        quota_definition_csv_file = open_support_file('test_quota_definitions.csv', __file__)

        post_data = {
            'preferential_rates_csv_data': preferential_rates_csv_file,
            'order_number_csv_data': order_number_csv_file,
            'quota_definition_csv_data': quota_definition_csv_file,
        }

        resp = valid_user_client.post(
            reverse(
                "reference_documents:reference-document-csv-upload"
            ),
            post_data
        )
        assert resp.status_code == 403

    def test_post_with_permissions(self, superuser_client):
        preferential_rates_csv_file = open_support_file('test_preferential_rates.csv', __file__)
        order_number_csv_file = open_support_file('test_order_numbers.csv', __file__)
        quota_definition_csv_file = open_support_file('test_quota_definitions.csv', __file__)

        post_data = {
            'preferential_rates_csv_data': preferential_rates_csv_file,
            'order_number_csv_data': order_number_csv_file,
            'quota_definition_csv_data': quota_definition_csv_file,
        }

        resp = superuser_client.post(
            reverse(
                "reference_documents:reference-document-csv-upload"
            ),
            post_data
        )
        assert resp.status_code == 200

@pytest.mark.reference_documents
class TestReferenceDocumentCsvUploadCreateSuccess:
    def test_get_without_permissions(self, valid_user_client):
        resp = valid_user_client.get(
            reverse(
                "reference_documents:reference-document-csv-upload-success"
            ),
        )
        assert resp.status_code == 403

    def test_get_with_permissions(self, superuser_client):
        resp = superuser_client.get(
            reverse(
                "reference_documents:reference-document-csv-upload-success"
            ),
        )
        assert resp.status_code == 200
