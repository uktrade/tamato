import logging
from hashlib import md5

from typing import Optional

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.transaction import atomic
from lxml import etree

from common.tests.util import validate_taric_xml_record_order, TaricDataAssertionError
from exporter.management.util import serialize_envelope_as_xml
from exporter.models import Upload
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


def validate_envelope(envelope):
    """Validate envelope content for XML issues and data order issues.

    raises DocumentInvalid | TaricDataAssertionError
    """
    with open(settings.TARIC_XSD) as xsd_file:
        schema = etree.XMLSchema(etree.parse(xsd_file))
        xml = etree.XML(envelope)

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
def upload_workbaskets() -> (Optional[str], Optional[BaseException]):
    """
    Upload workbaskets.

    :return: upload_filename | None, validation_exception [if workbasket data did not verify].

    Data validation errors are not raised as exceptions as that would cause the celery task
    to fail (and possibly to be retried automatically).
    """
    with atomic():
        envelope = WorkBasket.objects.filter(
            status=WorkflowStatus.READY_FOR_EXPORT
        ).envelope_of_transactions()
        envelope_data = serialize_envelope_as_xml(envelope)
        try:
            validate_envelope(envelope_data)
        except (TaricDataAssertionError, etree.DocumentInvalid):
            # Nothing to log here - validate_envelope has already logged the issue.
            raise
        except BaseException as e:
            logger.exception(e)
            raise

        envelope.save()

        content_file = ContentFile(envelope_data)
        upload = Upload()
        upload.envelope = envelope
        upload.file = content_file
        upload.checksum = md5("".encode("utf-8")).hexdigest()

        upload.notify_hmrc()

        # destination = storage.save(full_filename, content_file)
        logger.debug("Uploaded: %s", upload.filename)

        return upload.filename
