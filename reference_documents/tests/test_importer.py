import pytest

from common.tests.factories import GeographicalAreaFactory
from reference_documents.csv_importer.importer import ReferenceDocumentCSVImporter
from reference_documents.models import ReferenceDocumentVersionStatus, CSVUpload, ReferenceDocumentCsvUploadStatus
from reference_documents.models import RefOrderNumber
from reference_documents.tests import factories
from reference_documents.tests.factories import RefOrderNumberFactory, CSVUploadFactory, ReferenceDocumentVersionFactory

pytestmark = pytest.mark.django_db


# preferential rates CSV data
def mock_preferential_rates_csv_data():
    return """comm_code,rate,validity_start,validity_end,area_id,document_version
0100000000,0.00%,2024-01-01,,NZ,1.0
0200000000,5.00% + 147.00 GBP / 100 kg,2024-01-01,2028-12-31,NZ,1.0"""


def mock_preferential_rates_csv_data_invalid_date():
    return """comm_code,rate,validity_start,validity_end,area_id,document_version
0100000000,0.00%,2024-01-32,,NZ,1.0"""


def mock_preferential_rates_csv_data_invalid_area_id():
    return """comm_code,rate,validity_start,validity_end,area_id,document_version
0100000000,0.00%,2024-01-01,,XX,1.0"""


def mock_preferential_rates_csv_data_invalid_comm_code():
    return """comm_code,rate,validity_start,validity_end,area_id,document_version
ABC,0.00%,2024-01-01,,NZ,1.0"""


def mock_preferential_rates_csv_data_invalid_document_version():
    return """comm_code,rate,validity_start,validity_end,area_id,document_version
0100000000,0.00%,2024-01-01,,NZ,4.z"""


def mock_preferential_rates_csv_data_invalid_headers():
    return """aa,rate,validity_start,validity_end,area_id,document_version
0100000000,0.00%,2024-01-01,,NZ,4.4"""


# order number CSV data
def mock_order_number_csv_data():
    return """order_number,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059001,2023-01-01,,,,,NZ,1.0
059002,2023-01-01,,059001,1.3,EQ,NZ,1.0
059003,2023-01-01,2024-01-01,,,,NZ,1.0"""


def mock_order_number_csv_data_invalid_date():
    return """order_number,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059001,2023-01-41,,,,,NZ,1.0"""


def mock_order_number_csv_data_invalid_area_id():
    return """order_number,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059001,2023-01-01,,,,,AA,1.0"""


def mock_order_number_csv_data_invalid_document_version():
    return """order_number,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059001,2023-01-01,,,,,NZ,1.a"""


def mock_order_number_csv_data_invalid_headers():
    return """banana,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059001,2023-01-01,,,,,NZ,1.0"""

def mock_order_number_already_exists_csv_data():
    return """order_number,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059001,2023-01-01,,,,,NZ,1.0
059001,2023-01-01,,,,,NZ,1.0"""

def mock_order_number_parent_does_not_exist_csv_data():
    return """order_number,validity_start,validity_end,parent_order_number,coefficient,relationship_type,area_id,document_version,
059002,2023-01-01,,059001,1.3,EQ,NZ,1.0"""

# Quota definition CSV data
def mock_quota_definition_csv_data():
    return """order_number,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,0100000000,0.00%,200,tonnes,2023-01-01,2023-12-31,NZ,1.0
059001,0100000000,0.00%,400,tonnes,2024-01-01,2024-12-31,NZ,1.0
059001,0100000000,0.00%,400,tonnes,2025-01-01,,NZ,1.0"""


def mock_quota_definition_csv_data_invalid_date():
    return """order_number,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,0100000000,0.00%,200,tonnes,2023-01-41,2023-12-31,NZ,1.0"""


def mock_quota_definition_csv_data_invalid_area_id():
    return """order_number,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,0100000000,0.00%,200,tonnes,2023-01-01,2023-12-31,AA,1.0"""


def mock_quota_definition_csv_data_invalid_comm_code_content():
    return """order_number,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,AAAAAAAAAA,0.00%,200,tonnes,2023-01-01,2023-12-31,NZ,1.0"""

def mock_quota_definition_csv_data_invalid_comm_code_length():
    return """order_number,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,010000000,0.00%,200,tonnes,2023-01-01,2023-12-31,NZ,1.0"""


def mock_quota_definition_csv_data_invalid_document_version():
    return """order_number,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,0100000000,0.00%,200,tonnes,2023-01-01,2023-12-31,NZ,1.z"""


def mock_quota_definition_csv_data_invalid_headers():
    return """boop,comm_code,duty_rate,initial_volume,measurement,validity_start,validity_end,area_id,document_version
059001,0100000000,0.00%,200,tonnes,2023-01-01,2023-12-31,NZ,1.0"""

@pytest.mark.reference_documents
class TestReferenceDocumentCSVImporter:
    def test_init(self):
        csv_upload = CSVUploadFactory.create()
        target = ReferenceDocumentCSVImporter(csv_upload)

        assert target.csv_upload == csv_upload

    def test_run_empty_csv_upload_marks_csv_upload_as_errored(self):
        csv_upload = CSVUploadFactory.create()
        target = ReferenceDocumentCSVImporter(csv_upload)
        target.run()
        assert csv_upload.status == ReferenceDocumentCsvUploadStatus.ERRORED
        assert csv_upload.error_details == 'No CSV data to process, exiting.'

    @pytest.mark.parametrize("preferential_rates_csv_data,order_number_csv_data,quota_definition_csv_data,expected_status,error_details_contains", [
        # preferential rates CSV data
        (mock_preferential_rates_csv_data(), None, None, ReferenceDocumentCsvUploadStatus.COMPLETE, ''),
        (mock_preferential_rates_csv_data_invalid_date(), None, None, ReferenceDocumentCsvUploadStatus.ERRORED, 'ValidationError:“%(value)s” value has the correct format (YYYY-MM-DD) but it is an invalid date.'),
        (mock_preferential_rates_csv_data_invalid_area_id(), None, None, ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:Area ID does not exist in TAP data: XX'),
        (mock_preferential_rates_csv_data_invalid_comm_code(), None, None, ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:ABC is not a valid comm code, it can only contain numbers'),
        (mock_preferential_rates_csv_data_invalid_document_version(), None, None, ReferenceDocumentCsvUploadStatus.ERRORED, "ValueError:could not convert string to float: '4.z'"),
        (mock_preferential_rates_csv_data_invalid_headers(), None, None, ReferenceDocumentCsvUploadStatus.ERRORED, "ValueError:CSV data for preferential rates missing header comm_code"),
        # Order Number CSV data
        (None, mock_order_number_csv_data(), None, ReferenceDocumentCsvUploadStatus.COMPLETE, ''),
        (None, mock_order_number_csv_data_invalid_date(), None, ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:day is out of range for month'),
        (None, mock_order_number_csv_data_invalid_area_id(), None, ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:Area ID does not exist in TAP data: AA'),
        (None, mock_order_number_csv_data_invalid_document_version(), None, ReferenceDocumentCsvUploadStatus.ERRORED, "ValueError:could not convert string to float: '1.a'"),
        (None, mock_order_number_csv_data_invalid_headers(), None, ReferenceDocumentCsvUploadStatus.ERRORED, "ValueError:CSV data for order numbers missing header order_number"),
        (None, mock_order_number_already_exists_csv_data(), None, ReferenceDocumentCsvUploadStatus.ERRORED, "Exception:Order Number already exists, details : {'order_number': '059001', 'validity_start': '2023-01-01', 'validity_end': '', 'parent_order_number': '', 'coefficient': '', 'relationship_type': '', 'area_id': 'NZ', 'document_version': '1.0', '': None}, matched on order number and start_date."),
        (None, mock_order_number_parent_does_not_exist_csv_data(), None, ReferenceDocumentCsvUploadStatus.ERRORED, "Exception:Parent Order Number 059001 does not exist."),
        # Quota Definition CSV data
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data(), ReferenceDocumentCsvUploadStatus.COMPLETE, ''),
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data_invalid_date(), ReferenceDocumentCsvUploadStatus.ERRORED, 'ValidationError:“%(value)s” value has the correct format (YYYY-MM-DD) but it is an invalid date.'),
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data_invalid_area_id(), ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:Area ID does not exist in TAP data: AA'),
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data_invalid_comm_code_content(), ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:AAAAAAAAAA is not a valid comm code, it can only contain numbers'),
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data_invalid_comm_code_length(), ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:010000000 is not a valid comm code, it should be 10 characters long'),
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data_invalid_document_version(), ReferenceDocumentCsvUploadStatus.ERRORED, "ValueError:could not convert string to float: '1.z'"),
        (None, mock_order_number_csv_data(), mock_quota_definition_csv_data_invalid_headers(), ReferenceDocumentCsvUploadStatus.ERRORED, 'ValueError:CSV data for quota definitions missing header order_number'),
    ])
    def test_run_csv_upload_with_preferential_rates_csv_data(self, preferential_rates_csv_data, order_number_csv_data,quota_definition_csv_data, expected_status, error_details_contains):
        csv_upload = CSVUploadFactory.create(
            preferential_rates_csv_data=preferential_rates_csv_data,
            order_number_csv_data=order_number_csv_data,
            quota_definition_csv_data=quota_definition_csv_data,
        )
        # add geoarea
        GeographicalAreaFactory.create(area_id='NZ')
        target = ReferenceDocumentCSVImporter(csv_upload)

        target.run()
        assert csv_upload.status == expected_status
        assert csv_upload.error_details == error_details_contains

    def test_fails_when_ref_doc_version_not_editable(self):
        csv_upload = CSVUploadFactory.create(
            preferential_rates_csv_data=mock_preferential_rates_csv_data(),
            order_number_csv_data=mock_order_number_csv_data(),
            quota_definition_csv_data=mock_quota_definition_csv_data(),
        )
        # add geoarea
        GeographicalAreaFactory.create(area_id='NZ')
        ReferenceDocumentVersionFactory.create(reference_document__area_id='NZ', published=True, version='1.0')
        target = ReferenceDocumentCSVImporter(csv_upload)
        target.run()
        assert csv_upload.status ==  ReferenceDocumentCsvUploadStatus.ERRORED
        assert csv_upload.error_details == 'Exception:Reference document version NZ:1.0 has status PUBLISHED and can not be altered.'
