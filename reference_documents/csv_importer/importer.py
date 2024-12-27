import csv
import re
from datetime import datetime
from io import StringIO
from logging import getLogger

from django.db import transaction

from common.util import TaricDateRange
from geo_areas.models import GeographicalArea
from reference_documents.models import CSVUpload
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentCsvUploadStatus
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.models import ReferenceDocumentVersionStatus
from reference_documents.models import RefOrderNumber
from reference_documents.models import RefQuotaDefinition
from reference_documents.models import RefRate

logger = getLogger(__name__)


class ReferenceDocumentCSVImporter:
    def __init__(self, csv_upload: CSVUpload):
        self.csv_upload = csv_upload

    def run(self):

        if (
            not self.csv_upload.preferential_rates_csv_data
            and not self.csv_upload.order_number_csv_data
            and not self.csv_upload.quota_definition_csv_data
        ):
            # mark csv upload as errored, and add message
            self.csv_upload.status = ReferenceDocumentCsvUploadStatus.ERRORED
            self.csv_upload.error_details = "No CSV data to process, exiting."
            self.csv_upload.save()
        else:
            # process preferential rates
            try:
                self.csv_upload.processing()
                self.csv_upload.save()
                # make all changes or none, atomic transaction
                with transaction.atomic():
                    if self.csv_upload.preferential_rates_csv_data:
                        self.import_preferential_rates_csv_data()

                    # process order numbers
                    if self.csv_upload.order_number_csv_data:
                        self.import_order_number_csv_data()

                    # process quota definitions
                    if self.csv_upload.quota_definition_csv_data:
                        self.import_quota_definition_csv_data()

                self.csv_upload.completed()
                self.csv_upload.save()
            except Exception as ex:
                self.csv_upload.errored()
                # add error to CSV upload
                if hasattr(ex, "message"):
                    ex_message = ex.message
                else:
                    ex_message = ex
                self.csv_upload.error_details = f"{ex.__class__.__name__}:{ex_message}"
                self.csv_upload.save()

    def find_reference_document(self, area_id):
        """
        Checks the database to see if a reference document exists matching the area_id
        Args:
            area_id: the area id the reference document is associated with as a string

        Returns: ReferenceDocument, or none if not matched

        """
        ref_doc_ver_query = ReferenceDocument.objects.filter(
            area_id=area_id,
        )

        if ref_doc_ver_query.exists():
            return ref_doc_ver_query.first()

        return None

    def find_reference_document_version(
        self,
        reference_document_version: float,
        reference_document: ReferenceDocument,
        status=None,
    ):
        """

        Args:
            reference_document_version: the version of the reference document as a string
            reference_document: The reference document as a ReferenceDocument
            status: Optional, the status of the reference document from the choices available from ReferenceDocumentVersionStatus.choices

        Returns: boolean, True if matched to a reference document version that is editable, otherwise false

        """
        if status:
            ref_doc_ver_query = ReferenceDocumentVersion.objects.filter(
                version=reference_document_version,
                reference_document=reference_document,
                status=status,
            )
        else:
            ref_doc_ver_query = ReferenceDocumentVersion.objects.filter(
                version=reference_document_version,
                reference_document=reference_document,
            )

        if ref_doc_ver_query.exists():
            return ref_doc_ver_query.first()

        return None

    @staticmethod
    def verify_area_id_exists(area_id):
        if (
            not GeographicalArea.objects.latest_approved()
            .filter(area_id=area_id)
            .exists()
        ):
            raise ValueError(f"Area ID does not exist in TAP data: {area_id}")

    def verify_comm_code(self, comm_code):
        if not bool(re.match("^[0123456789]+$", comm_code)):
            raise ValueError(
                f"{comm_code} is not a valid comm code, it can only contain numbers",
            )

        if len(comm_code) != 10:
            raise ValueError(
                f"{comm_code} is not a valid comm code, it should be 10 characters long",
            )

    def import_preferential_rates_csv_data(self):
        logger.info(f" -- IMPORTING PREFERENTIAL RATES")
        data = self.get_dictionary_from_csv_data(
            self.csv_upload.preferential_rates_csv_data,
        )

        # verify headers
        expected_headers = [
            "comm_code",
            "rate",
            "validity_start",
            "validity_end",
            "area_id",
            "document_version",
        ]

        for header in expected_headers:
            if header not in data[0].keys():
                raise ValueError(
                    f"CSV data for preferential rates missing header {header}",
                )

        for row in data:
            self.verify_area_id_exists(row["area_id"])
            self.verify_comm_code(row["comm_code"])
            reference_document_version = self.get_or_create_reference_document_version(
                row,
            )

            # check if data row exists, use comm code and start date
            matching_row = reference_document_version.ref_rates.filter(
                commodity_code=row["comm_code"],
                valid_between__startswith=row["validity_start"],
            )

            start_date = datetime(
                *[int(x) for x in row["validity_start"].split("-")],
            ).date()
            end_date = row["validity_end"]

            if end_date == "":
                end_date = None
            else:
                end_date = datetime(
                    *[int(x) for x in row["validity_end"].split("-")],
                ).date()

            if matching_row.exists():
                raise Exception(
                    f"Preferential Rate already exists, details : {row}, matched on commodity_code and start_date.",
                )
            else:
                RefRate.objects.create(
                    reference_document_version=reference_document_version,
                    commodity_code=row["comm_code"],
                    duty_rate=row["rate"],
                    valid_between=TaricDateRange(start_date, end_date),
                )
        logger.info(f" -- COMPLETED IMPORTING PREFERENTIAL RATES : count: {len(data)}")

    def get_or_create_reference_document_version(self, row):
        # check if reference document exists
        if self.find_reference_document(row["area_id"]):
            # use existing reference document
            reference_document = ReferenceDocument.objects.get(
                area_id=row["area_id"],
            )
        else:
            # create new reference document
            reference_document = ReferenceDocument.objects.create(
                area_id=row["area_id"],
                title=f'Reference document for area ID {row["area_id"]}',
            )
        # check if reference document version is available and editable
        reference_document_version = self.find_reference_document_version(
            float(row["document_version"]),
            reference_document,
        )
        # raise exception if the version exists but is not in editing
        if reference_document_version:
            if (
                reference_document_version.status
                != ReferenceDocumentVersionStatus.EDITING
            ):
                raise Exception(
                    f"Reference document version {reference_document_version.reference_document.area_id}:{reference_document_version.version} has status {reference_document_version.status} and can not be altered.",
                )
        else:
            reference_document_version = ReferenceDocumentVersion.objects.create(
                version=row["document_version"],
                reference_document=reference_document,
            )
        return reference_document_version

    def import_order_number_csv_data(self):
        data = self.get_dictionary_from_csv_data(self.csv_upload.order_number_csv_data)
        logger.info(f" -- IMPORTING ORDER NUMBERS")

        expected_headers = [
            "order_number",
            "validity_start",
            "validity_end",
            "parent_order_number",
            "coefficient",
            "relationship_type",
            "area_id",
            "document_version",
        ]

        for header in expected_headers:
            if header not in data[0].keys():
                raise ValueError(f"CSV data for order numbers missing header {header}")

        # only ones without parents
        for row in data:
            self.verify_area_id_exists(row["area_id"])

            if row["parent_order_number"] != "":
                continue
            self.process_order_number(row)

        # process order numbers with parents
        for row in data:
            if row["parent_order_number"] == "":
                continue

            self.process_order_number(row)
        logger.info(f" -- COMPLETED IMPORTING ORDER NUMBERS : count: {len(data)}")

    def process_order_number(self, row):
        reference_document_version = self.get_or_create_reference_document_version(row)
        start_date = datetime(
            *[int(x) for x in row["validity_start"].split("-")],
        ).date()
        end_date = row["validity_end"]
        if end_date == "":
            end_date = None
        else:
            end_date = datetime(
                *[int(x) for x in row["validity_end"].split("-")],
            ).date()
        # check if data row exists, use comm code and start date
        matching_row = reference_document_version.ref_order_numbers.filter(
            order_number=row["order_number"],
            valid_between__startswith=row["validity_start"],
        )
        if matching_row.exists():
            raise Exception(
                f"Order Number already exists, details : {row}, matched on order number and start_date.",
            )
        else:
            coefficient = row["coefficient"]
            parent_order_number = row["parent_order_number"]
            relationship_type = row["relationship_type"]

            if coefficient == "":
                coefficient = None

            if parent_order_number == "":
                parent_order_number = None
            else:
                parent_order_number_query = (
                    reference_document_version.ref_order_numbers.filter(
                        order_number=parent_order_number,
                    )
                )
                if parent_order_number_query.exists():
                    parent_order_number = parent_order_number_query.first()
                else:
                    raise Exception(
                        f"Parent Order Number {parent_order_number} does not exist.",
                    )

            if relationship_type == "":
                relationship_type = None

            RefOrderNumber.objects.create(
                reference_document_version=reference_document_version,
                order_number=row["order_number"],
                valid_between=TaricDateRange(start_date, end_date),
                coefficient=coefficient,
                main_order_number=parent_order_number,
                relation_type=relationship_type,
            )

    def import_quota_definition_csv_data(self):
        data = self.get_dictionary_from_csv_data(
            self.csv_upload.quota_definition_csv_data,
        )
        logger.info(f" -- IMPORTING QUOTA DEFINITIONS")

        expected_headers = [
            "order_number",
            "comm_code",
            "duty_rate",
            "initial_volume",
            "measurement",
            "validity_start",
            "validity_end",
            "area_id",
            "document_version",
        ]

        for header in expected_headers:
            if header not in data[0].keys():
                raise ValueError(
                    f"CSV data for quota definitions missing header {header}",
                )

        for row in data:
            self.verify_area_id_exists(row["area_id"])
            self.verify_comm_code(row["comm_code"])
            reference_document_version = self.get_or_create_reference_document_version(
                row,
            )

            # check if data row exists, use comm code and start date
            matching_row = reference_document_version.ref_quota_definitions().filter(
                commodity_code=row["comm_code"],
                ref_order_number__order_number=row["order_number"],
                valid_between__startswith=row["validity_start"],
            )

            start_date = datetime(
                *[int(x) for x in row["validity_start"].split("-")],
            ).date()
            end_date = row["validity_end"]

            if end_date == "":
                end_date = None
            else:
                end_date = datetime(
                    *[int(x) for x in row["validity_end"].split("-")],
                ).date()

            order_number = reference_document_version.ref_order_numbers.filter(
                order_number=row["order_number"],
            )

            if not order_number.exists():
                raise Exception(f'Order Number {row["order_number"]} does not exist.')

            volume = float(row["initial_volume"])
            measurement = row["measurement"]

            if matching_row.exists():
                raise Exception(
                    f"Quota Definition already exists, details : {row}, matched on commodity_code, order number and start_date.",
                )
            else:
                RefQuotaDefinition.objects.create(
                    commodity_code=row["comm_code"],
                    duty_rate=row["duty_rate"],
                    valid_between=TaricDateRange(start_date, end_date),
                    ref_order_number=order_number.first(),
                    volume=volume,
                    measurement=measurement,
                )
        logger.info(f" -- COMPLETED IMPORTING QUOTA DEFINITIONS : count: {len(data)}")

    def get_dictionary_from_csv_data(self, string):
        csv_string_io = StringIO(string)
        csv_reader = csv.DictReader(csv_string_io)
        data = [row for row in csv_reader]
        return data
