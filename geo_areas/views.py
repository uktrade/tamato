from django.shortcuts import render
from rest_framework import permissions
from rest_framework import viewsets

from common.views import TamatoListView
from common.views import TrackedModelDetailView
from geo_areas.filters import GeographicalAreaFilter
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.serializers import GeographicalAreaSerializer


class GeoAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows geographical areas to be viewed.
    """

    queryset = GeographicalArea.objects.current().prefetch_related("descriptions")
    serializer_class = GeographicalAreaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "area_code"]


class GeographicalAreaList(TamatoListView):
    queryset = GeographicalArea.objects.current().prefetch_related("descriptions")
    template_name = "geo_areas/list.jinja"
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "descriptions__description"]


class GeographicalAreaDetail(TrackedModelDetailView):
    model = GeographicalArea
    template_name = "geo_areas/detail.jinja"
    queryset = GeographicalArea.objects.current().prefetch_related("descriptions")
