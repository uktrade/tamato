import logging
import os
import tempfile
from hashlib import md5
from typing import Optional, Tuple

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.transaction import atomic
from lxml import etree

from common.tests.util import TaricDataAssertionError
from common.tests.util import validate_taric_xml_record_order
from exporter.models import Upload
from common.serializers import EnvelopeSerializer
from taric.models import Envelope, EnvelopeTransaction
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def validate_envelope(envelope_file, skip_declaration=False):
    """Validate envelope content for XML issues and data order issues.

    raises DocumentInvalid | TaricDataAssertionError
    """
    with open(settings.TARIC_XSD) as xsd_file:
        if skip_declaration:
            pos = envelope_file.position()
            xml_declaration = envelope_file.read(len(XML_DECLARATION))
            if xml_declaration != XML_DECLARATION:
                logger.warning(
                    "Expected XML declaration first line of envelope to be XML encoding declaration, but found: ",
                    xml_declaration,
                )
                envelope_file.seek(pos)

        schema = etree.XMLSchema(etree.parse(xsd_file))
        xml = etree.parse(envelope_file)

        try:
            schema.assertValid(xml)
        except etree.DocumentInvalid as e:
            logger.error("Envelope did not validate against XSD: %s", str(e.error_log))
            raise
        try:
            validate_taric_xml_record_order(xml)
        except TaricDataAssertionError as e:
            logger.error(e.args[0])
            raise


@shared_task
@atomic
def upload_workbaskets() -> Tuple[bool, str]:
    """
    Upload workbaskets.

    Returns a bool for success and a message for the user.
    """
    workbaskets = WorkBasket.objects.filter(status=WorkflowStatus.READY_FOR_EXPORT)
    if not workbaskets:
        msg = "Nothing to upload:  No workbaskets with status READY_FOR_EXPORT."
        logger.info(msg)
        return False, msg

    # tracked_models:  will be serialized, then added to an envelope for uploaded.
    transactions = workbaskets.ordered_transactions()
    tracked_models = transactions.ordered_tracked_models()
    if not tracked_models:
        msg = f"Nothing to upload:  {workbaskets.count()} Workbaskets READY_FOR_EXPORT but none contain any transactions."
        logger.info(msg)
        return False, msg

    # Write to a temporary file so that output can be validated afterwards.
    with tempfile.TemporaryFile() as envelope_file:
        envelope = Envelope.new_envelope()

        with EnvelopeSerializer(
            envelope_file, envelope_id=int(envelope.envelope_id)
        ) as env:
            env.render_transaction(tracked_models)

        envelope_file.seek(os.SEEK_SET)
        try:
            validate_envelope(envelope_file)
        except (TaricDataAssertionError, etree.DocumentInvalid):
            # Nothing to log here - validate_envelope has already logged the issue.
            raise
        except BaseException as e:
            logger.exception(e)
            raise

        envelope_transactions = [
            EnvelopeTransaction(order=order, envelope=envelope, transaction=transaction)
            for order, transaction in enumerate(transactions)
        ]

        EnvelopeTransaction.objects.bulk_create(envelope_transactions)
        envelope.save()

        envelope_file.seek(os.SEEK_SET)
        content_file = ContentFile(envelope_file.read())
        upload = Upload()
        upload.envelope = envelope
        upload.file = content_file

        envelope_file.seek(os.SEEK_SET)
        upload.checksum = md5(envelope_file.read()).hexdigest()

        upload.file.save(upload.filename, content_file)
        upload.notify_hmrc()  # sets notification_sent

        workbaskets.update(status=WorkflowStatus.SENT_TO_CDS)

        logger.debug("Uploaded: %s", upload.filename)
        return True, upload.filename
