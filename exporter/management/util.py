from django.test import RequestFactory
from exporter.views import EnvelopeViewSet
from taric.models import Envelope


def serialize_envelope_as_xml(envelope: Envelope) -> bytes:
    """Render envelope as XML"""
    envelope_id = envelope.pk
    request = RequestFactory().get(f"/api/envelopes/{envelope_id}.xml")
    view = EnvelopeViewSet.as_view({"get": "list"})
    response = view(request, envelope, format="xml")

    envelope_data = response.render().content
    return envelope_data
