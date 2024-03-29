import logging
import os
import tempfile
from hashlib import md5
from typing import Dict
from typing import Sequence

from apiclient.exceptions import APIRequestError
from botocore.exceptions import ConnectionError
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.db.transaction import atomic

from common.util import TableLock
from exporter import sqlite
from exporter.models import Upload
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.serializers import RenderedTransactions
from exporter.serializers import validate_rendered_envelopes
from exporter.util import UploadTaskResultData
from exporter.util import dit_file_generator
from exporter.util import exceptions_as_messages
from taric.models import Envelope
from taric.models import EnvelopeTransaction
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class RaceCondition(Exception):
    pass


@atomic
def upload_and_create_envelopes(
    workbaskets: QuerySet,
    rendered_envelopes: Sequence[RenderedTransactions],
    first_envelope_id,
) -> UploadTaskResultData:
    """
    Upload Envelope data to the the s3 and create artifacts in the database.

    Side effects on success:
    Create Envelope, EnvelopeTransaction and Upload objects in the database and upload envelope XML to an S3 object.

    :return: :class:`~exporter.util.UploadTaskResultData`.
    """
    # upload_status holds data to pass to the next Task, including messages to the user.
    upload_status = UploadTaskResultData()

    current_envelope_id = first_envelope_id
    for rendered_envelope in rendered_envelopes:
        envelope = Envelope.new_envelope()
        if current_envelope_id != int(envelope.envelope_id):
            logger.error(
                "Envelope created out of sequence: %s != %i this may be due to simultaneous updates causing a race "
                "condition.",
                (current_envelope_id, int(envelope.envelope_id)),
            )
            raise RaceCondition(
                f"Envelope out of sequence: {envelope.envelope_id} != {current_envelope_id}",
            )
        current_envelope_id = int(envelope.envelope_id)

        envelope_transactions = [
            EnvelopeTransaction(order=order, envelope=envelope, transaction=transaction)
            for order, transaction in enumerate(rendered_envelope.transactions)
        ]
        EnvelopeTransaction.objects.bulk_create(envelope_transactions)
        envelope.save()

        rendered_envelope.output.seek(0, os.SEEK_SET)
        content_file = ContentFile(rendered_envelope.output.read())
        upload = Upload()
        upload.envelope = envelope
        upload.file = content_file

        rendered_envelope.output.seek(0, os.SEEK_SET)
        upload.checksum = md5(rendered_envelope.output.read()).hexdigest()

        upload.file.save(upload.filename, content_file)
        upload_status.add_upload_pk(upload.pk)

        logger.info("Workbasket saved to CDS S3 bucket")

        logger.debug("Uploaded: %s", upload.filename)
        upload_status.add_envelope_messages(
            envelope.envelope_id,
            [f"Uploaded {upload.filename}"],
        )
    return upload_status


@shared_task(
    bind=True,
    default_retry_delay=settings.EXPORTER_UPLOAD_DEFAULT_RETRY_DELAY,
    max_retries=settings.EXPORTER_UPLOAD_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.EXPORTER_UPLOAD_RETRY_BACKOFF_MAX,
    retry_jitter=True,
)
@TableLock.acquire_lock(Envelope, lock="SHARE")
def upload_workbasket_envelopes(self, upload_status_data) -> Dict:
    """
    Upload workbaskets.

    :return :class:`~exporter.util.UploadTaskResultData`: object with user readable feedback on task status.
    """
    upload_status = UploadTaskResultData(**upload_status_data)
    workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.QUEUED)

    if not workbaskets:
        msg = "Nothing to upload:  No workbaskets with status QUEUED."
        logger.info(msg)
        return dict(upload_status.add_messages([msg]))

    # transactions: will be serialized, then added to an envelope for upload.
    transactions = workbaskets.ordered_transactions()

    if not transactions:
        msg = f"Nothing to upload:  {workbaskets.count()} Workbaskets QUEUED but none contain any transactions."
        logger.info(msg)
        return dict(upload_status.add_messages([msg]))

    first_envelope_id = int(Envelope.next_envelope_id())
    # Envelope XML is written to temporary files for validation before anything is created
    # in the database or uploaded to s3.
    with tempfile.TemporaryDirectory(prefix="dit-tamato_") as temporary_directory:
        output_file_constructor = dit_file_generator(
            temporary_directory,
            first_envelope_id,
        )

        serializer = MultiFileEnvelopeTransactionSerializer(
            output_file_constructor,
            envelope_id=first_envelope_id,
            max_envelope_size=settings.EXPORTER_MAXIMUM_ENVELOPE_SIZE,
        )

        rendered_envelopes = list(serializer.split_render_transactions(transactions))

        envelope_errors = validate_rendered_envelopes(rendered_envelopes)
        if envelope_errors:
            for envelope_id, errors in exceptions_as_messages(envelope_errors).items():
                upload_status.add_envelope_errors(envelope_id, errors)
            return dict(upload_status)

        # Transaction envelope data XML is valid, ready for upload to s3 and creation
        # of corresponding database objects.
        #
        # Feedback for the user is added to a :class:`~exporter.util.UploadTaskResultData` and serialized
        # so that it can be safely returned in the Celery task result.
        try:
            upload_status.update(
                upload_and_create_envelopes(
                    workbaskets,
                    rendered_envelopes,
                    first_envelope_id,
                ),
            )
            return dict(upload_status)
        except ConnectionError as e:
            # Connection issue during upload.
            if settings.EXPORTER_UPLOAD_MAX_RETRIES:
                logger.info(
                    "%s uploading attempting to upload envelope. endpoint: %s error: %s",
                    type(e),
                    e.kwargs.get("endpoint_url"),
                    e.kwargs.get("error"),
                )
                self.retry()
            else:
                raise


@shared_task(
    bind=True,
    default_retry_delay=settings.EXPORTER_UPLOAD_DEFAULT_RETRY_DELAY,
    max_retries=settings.EXPORTER_UPLOAD_MAX_RETRIES,
    retry_backoff=True,
    retry_backoff_max=settings.EXPORTER_UPLOAD_RETRY_BACKOFF_MAX,
    retry_jitter=True,
)
def send_upload_notifications(self, upload_status_data):
    upload_status = UploadTaskResultData(**upload_status_data)
    if "upload_pks" not in upload_status:
        return dict(upload_status.add_messages(["No uploads to notify HMRC about."]))

    if settings.EXPORTER_DISABLE_NOTIFICATION:
        logger.info("Notifications are disabled.")
        return dict(upload_status.add_messages(["Notifications are disabled."]))

    for upload in Upload.objects.filter(
        pk__in=upload_status["upload_pks"],
        notification_sent__isnull=True,
    ):
        try:
            upload.notify_hmrc()
        except APIRequestError as e:
            # Connection issue during notification.
            logger.warning(f"{type(e)} notifying HMRC {e.message} {e.info}")
            if settings.EXPORTER_UPLOAD_MAX_RETRIES and (
                e.status_code is None or e.status_code >= 500
            ):
                # This logic was ported from 'retrying' and applied to celery [1]
                # [1] https://github.com/MikeWooster/api-client/blob/master/apiclient/retrying.py#L25
                self.retry()
            else:
                raise

    return dict(upload_status)


# Run upload and notification as separate tasks, so the task queue isn't blocked by a failure in either.
upload_workbaskets = (
    upload_workbasket_envelopes.s(upload_status_data={}) | send_upload_notifications.s()
)

export_and_upload_sqlite = sqlite.tasks.export_and_upload_sqlite
