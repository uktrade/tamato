from logging import getLogger

from common.celery import app
from reference_documents.check.check_runner import Checks
from reference_documents.csv_importer.importer import ReferenceDocumentCSVImporter
from reference_documents.models import CSVUpload
from reference_documents.models import ReferenceDocumentVersion

logger = getLogger(__name__)


@app.task
def run_alignment_check(
    reference_document_version_id: int,
):
    """
    Task for running alignment check.

    The task executes alignment checks against a reference document version and
    records the results in the TAP database for later review.
    """

    logger.info(
        f"RUNNING ALIGNMENT CHECKS : ReferenceDocumentVersion: {reference_document_version_id}",
    )

    ref_doc_ver = ReferenceDocumentVersion.objects.get(pk=reference_document_version_id)

    logger.info(
        f"Reference Document Version Details:\n"
        + f" - Geo Area : {ref_doc_ver.reference_document.area_id}\n"
        + f" - Pref Rates : {ref_doc_ver.ref_rates.count()}\n"
        + f" - Order Numbers : {ref_doc_ver.ref_order_numbers.count()}\n"
        + f" - Quota Defs : {ref_doc_ver.ref_quota_definitions().count()}",
    )

    check_runner = Checks(ref_doc_ver)
    check_runner.run()

    logger.info(
        f"COMPLETED ALIGNMENT CHECKS : ReferenceDocumentVersion: {reference_document_version_id}",
    )


@app.task
def import_reference_document_data(
    csv_upload_id: int,
):
    """
    Task for running alignment check.

    The task executes alignment checks against a reference document version and
    records the results in the TAP database for later review.
    """

    logger.info(
        f"RUNNING REFERENCE DOCUMENT CSV UPLOAD : csv_upload_id: {csv_upload_id}",
    )

    csv_upload = CSVUpload.objects.get(pk=csv_upload_id)

    uploaded_data_types = []
    if csv_upload.preferential_rates_csv_data:
        uploaded_data_types.append("preferential rates")
    if csv_upload.order_number_csv_data:
        uploaded_data_types.append("Order Numbers")
    if csv_upload.quota_definition_csv_data:
        uploaded_data_types.append("Quota Definitions")

    logger.info(
        f"Reference Document CSV upload details:\n"
        + f" - Upload includes the following : {', '.join(uploaded_data_types)}",
    )

    csv_importer = ReferenceDocumentCSVImporter(csv_upload)
    csv_importer.run()

    logger.info(
        f"COMPLETED REFERENCE DOCUMENT CSV UPLOAD : csv_upload_id: {csv_upload_id}",
    )
