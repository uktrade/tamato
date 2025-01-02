import pytest

from reference_documents.models import CSVUpload
from reference_documents.tests.factories import CSVUploadFactory

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestCsvUpload:
    def test_init(self):
        target = CSVUpload()

        assert target.error_details is None
        assert target.status == "PENDING"
        assert target.preferential_rates_csv_data is None
        assert target.order_number_csv_data is None
        assert target.quota_definition_csv_data is None

    def test_errored(self):
        target = CSVUploadFactory.create(processing=True)
        target.errored()
        assert target.status == "ERRORED"

    def test_processing(self):
        target = CSVUploadFactory.create()
        target.processing()
        assert target.status == "PROCESSING"

    def test_completed(self):
        target = CSVUploadFactory.create(processing=True)
        target.completed()
        assert target.status == "COMPLETE"

    def test_csv_content_types(self):
        target = CSVUploadFactory.create(
            preferential_rates_csv_data="some data",
            order_number_csv_data="some data",
            quota_definition_csv_data="some data",
        )
        assert (
            target.csv_content_types()
            == "Preferential rates, Order numbers, Quota definitions"
        )
