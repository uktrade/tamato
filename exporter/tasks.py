import logging

from lxml import etree
from pathlib import Path
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from lxml.etree import DocumentInvalid

from common.tests.util import validate_taric_xml_record_order, TaricDataAssertionError
from exporter.management.commands.util import (
    get_envelope_filename,
    get_envelope_of_active_workbaskets,
)  # TODO replace with Andys code
from exporter.storages import HMRCStorage
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
        except DocumentInvalid as err:
            logger.error(
                "Envelope did not validate against XSD: %s", str(err.error_log)
            )
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
    workbaskets = WorkBasket.objects.prefetch_ordered_tracked_models().filter(
        status=WorkflowStatus.READY_FOR_EXPORT
    )

    envelope = get_envelope_of_active_workbaskets(workbaskets)
    try:
        validate_envelope(envelope)
    except (TaricDataAssertionError, etree.DocumentInvalid) as exc:
        # Nothing to log here - validate_envelope has already logged the issue.
        return None, exc
    else:
        exc = None

    filename = get_envelope_filename(1)
    full_filename = str(Path(settings.HMRC_STORAGE_DIRECTORY) / filename)

    content_file = ContentFile(envelope)
    storage = HMRCStorage()
    destination = storage.save(full_filename, content_file)
    logger.debug(f"Uploaded: {destination}")

    return destination, exc
