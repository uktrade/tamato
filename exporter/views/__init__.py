from django_filters import rest_framework as filters
from rest_framework import renderers
from rest_framework import viewsets

from common.renderers import TaricXMLRenderer
from exporter.models import Envelope
from exporter.serializers import EnvelopeSerializer


class EnvelopeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows envelopes to be viewed.
    """

    queryset = Envelope.objects.prefetch_related("transactions")
    filter_backends = (filters.DjangoFilterBackend,)
    serializer_class = EnvelopeSerializer
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.BrowsableAPIRenderer,
        TaricXMLRenderer,
    ]
    template_name = "exporter/taric/envelope_list.xml"

    def get_template_names(self, *args, **kwargs):
        if self.detail:
            return ["exporter/taric/envelope_detail.xml"]
        return ["exporter/taric/envelope_list.xml"]
