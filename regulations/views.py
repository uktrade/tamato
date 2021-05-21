from rest_framework import viewsets

from common.views import TamatoListView
from common.views import TrackedModelDetailView
from regulations import models
from regulations.filters import RegulationFilter
from regulations.filters import RegulationFilterBackend
from regulations.models import Regulation
from regulations.serializers import RegulationSerializer


class RegulationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows regulations to be viewed."""

    queryset = Regulation.objects.latest_approved().select_related("regulation_group")
    serializer_class = RegulationSerializer
    filter_backends = [RegulationFilterBackend]


class RegulationList(TamatoListView):
    """UI endpoint that allows regulations to be viewed."""

    queryset = Regulation.objects.latest_approved().select_related("regulation_group")
    template_name = "regulations/list.jinja"
    filterset_class = RegulationFilter
    search_fields = ["regulation_id", "pk"]


class RegulationDetail(TrackedModelDetailView):
    required_url_kwargs = ("regulation_id",)

    model = models.Regulation
    template_name = "regulations/detail.jinja"
    queryset = Regulation.objects.latest_approved().select_related("regulation_group")
