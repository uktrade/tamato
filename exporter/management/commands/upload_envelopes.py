import hashlib
import sys
from typing import Sequence

import xmlschema

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import BaseCommand
from django.test import RequestFactory

from workbaskets.views import WorkBasketViewSet
from workbaskets.models import WorkBasket, WorkflowStatus


ENVELOPE_XSD = f"{settings.BASE_DIR}/common/assets/envelope.xsd"


def get_envelope(workbaskets: Sequence[WorkBasket]):
    # Re-use the DRF infrastructure, data is exactly the same
    # as can be output via views for testing.
    view = WorkBasketViewSet.as_view({"get": "list"})
    request = RequestFactory().get(
        "/api/workbaskets.xml", status=WorkflowStatus.READY_FOR_EXPORT
    )

    response = view(request, workbaskets, format="xml", envelope_id=1)
    return response.render().content


def upload_envelopes():
    # TODO
    # Can use test client and view with status=authorized ?
    # Save to django storage setup to s3

    # This uses the test client to grab data via a view, this is a bit of a hack
    # but seems does provide a really simple API to get the data in the required
    # forms
    workbaskets = WorkBasket.objects.prefetch_ordered_tracked_models().filter(
        status=WorkflowStatus.READY_FOR_EXPORT
    )

    envelope = get_envelope(workbaskets)

    content_file = ContentFile(envelope)

    xml_validates = xmlschema.is_valid(content_file, ENVELOPE_XSD)

    if not xml_validates:
        sys.exit(f"Envelope did not validate against XSD {ENVELOPE_XSD}")

    content_hash = hashlib.sha256(envelope).hexdigest()
    filename = f"{content_hash}.xml"
    default_storage.save(f"tohmrc/staging/{filename}", content_file)


class Command(BaseCommand):
    help = "Generate envelope files and upload them to S3"

    def handle(self, *args, **options):
        upload_envelopes()
