from django.shortcuts import render
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import viewsets

from regulations.filters import RegulationFilterBackend
from regulations.models import Regulation
from regulations.serializers import RegulationSerializer


class RegulationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows regulations to be viewed."""

    queryset = Regulation.objects.current().select_related("regulation_group")
    serializer_class = RegulationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [RegulationFilterBackend]
    search_fields = ["regulation_id"]


class RegulationUIViewSet(RegulationViewSet):
    """UI endpoint that allows regulations to be viewed."""

    renderer_classes = [renderers.TemplateHTMLRenderer]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request,
            "regulations/list.jinja",
            context={"object_list": queryset},
        )

    def retrieve(self, request, *args, **kwargs):
        return render(
            request,
            "regulations/detail.jinja",
            context={"regulation": self.get_object()},
        )
