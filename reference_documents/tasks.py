from logging import getLogger

from common.celery import app
from reference_documents.check.check_runner import Checks
from reference_documents.models import ReferenceDocumentVersion

logger = getLogger(__name__)


@app.task
def run_alignment_check(
        reference_document_version_id: int,
):
    """
    Task for importing an XML chunk into the database.

    This task must ensure the chunks workbasket_status reflects the import
    process, whether it is currently running, errored or done. Once complete it
    is also responsible for finding and setting up the next chunk tasks.
    """

    logger.info(
        f"RUNNING ALIGNMENT CHECKS : ReferenceDocumentVersion: {reference_document_version_id}"
    )

    ref_doc_ver = ReferenceDocumentVersion.objects.get(pk=reference_document_version_id)

    logger.info(
        f"Reference Document Version Details:\n" +
        f" - Geo Area : {ref_doc_ver.reference_document.area_id}\n" +
        f" - Pref Rates : {ref_doc_ver.preferential_rates.count()}\n" +
        f" - Order Numbers : {ref_doc_ver.ref_order_numbers.count()}\n" +
        f" - Quota Defs : {ref_doc_ver.preferential_quotas().count()}"
    )

    check_runner = Checks(ref_doc_ver)
    check_runner.run()

    logger.info(
        f"COMPLETED ALIGNMENT CHECKS : ReferenceDocumentVersion: {reference_document_version_id}"
    )
