import logging
import os
import tempfile
from hashlib import md5
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.db.transaction import atomic

from exporter.models import Upload
from exporter.serializers import MultiFileEnvelopeTransactionSerializer
from exporter.serializers import RenderedTransactions
from exporter.serializers import validate_rendered_envelopes
from exporter.util import dit_file_generator
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
) -> Dict[Union[int, None], str]:
    # {envelope_id: message} User messages can be returned to the caller of the task.
    user_messages = {}
    current_envelope_id = first_envelope_id
    for rendered_envelope in rendered_envelopes:
        envelope = Envelope.new_envelope()
        if current_envelope_id != int(envelope.envelope_id):
            # TODO consider locking the table for writes instead
            logger.error(
                "Envelope created out of sequence: %s != %s this may due to simultaneous updates causing a race condition.",
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
        if settings.EXPORTER_DISABLE_NOTIFICATION:
            logger.info("HMRC notification disabled.")
        else:
            logger.info("Notify HMRC of upload, %s", upload.filename)
            upload.notify_hmrc()  # sets notification_sent

        logger.info("Workbasket sent to CDS")
        workbaskets.update(status=WorkflowStatus.SENT_TO_CDS)

        logger.debug("Uploaded: %s", upload.filename)
        user_messages[envelope.envelope_id] = f"Uploaded {upload.filename}"
    return user_messages


@shared_task
@atomic
def upload_workbaskets() -> Tuple[bool, Optional[Dict[Union[str, None], str]]]:
    """
    Upload workbaskets.

    Returns a bool for success and dict of user messages keyed by envelope_id or
    None.
    """
    workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.READY_FOR_EXPORT)
    if not workbaskets:
        msg = "Nothing to upload:  No workbaskets with status READY_FOR_EXPORT."
        logger.info(msg)
        return False, {None: msg}

    # transactions:  will be serialized, then added to an envelope for uploaded.
    transactions = workbaskets.ordered_transactions()

    if not transactions:
        msg = f"Nothing to upload:  {workbaskets.count()} Workbaskets READY_FOR_EXPORT but none contain any transactions."
        logger.info(msg)
        return False, {None: msg}

    first_envelope_id = int(Envelope.next_envelope_id())
    # Write files to a temporary, so they can all be validated before uploading.
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

        invalid_envelopes = validate_rendered_envelopes(rendered_envelopes)
        error_messages = {
            envelope_id: f"Envelope {envelope_id:06} was invalid {exception}"
            for envelope_id, exception in invalid_envelopes.items()
        }

        if error_messages:
            return False, error_messages

        # Transactions envelopes are all valid, and ready for upload.
        user_messages = upload_and_create_envelopes(
            workbaskets,
            rendered_envelopes,
            first_envelope_id,
        )

        return True, user_messages
