import datetime
from typing import Sequence

from django.conf import settings
from django.test import RequestFactory
from lxml import etree

from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus
from workbaskets.views import WorkBasketViewSet


def get_envelope_of_active_workbaskets(workbaskets: Sequence[WorkBasket]) -> bytes:
    """Return bytes object; Envelope XML of workbaskets ready for export."""
    # Re-use the DRF infrastructure, so data is exactly the same
    # as can be output via views for testing.
    view = WorkBasketViewSet.as_view({"get": "list"})
    request = RequestFactory().get(
        "/api/workbaskets.xml", status=WorkflowStatus.READY_FOR_EXPORT
    )

    response = view(request, workbaskets, format="xml", envelope_id=1)
    envelope = response.render().content
    return envelope


def validate_envelope_xml(envelope: bytes) -> bool:
    """Validate xml contained in a bytes against the envelope XSD"""
    with open(settings.TARIC_XSD) as xsd_file:
        schema = etree.XMLSchema(etree.parse(xsd_file))
        xml = etree.XML(envelope)
        return schema.validate(xml)


def get_envelope_filename(counter) -> str:
    now = datetime.datetime.now()
    return f"DIT{str(now.year)[:2]}{counter:04}.xml"
