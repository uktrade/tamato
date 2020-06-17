from django.shortcuts import render
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import viewsets

from geo_areas.filters import GeographicalAreaFilter
from geo_areas.models import GeographicalArea
from geo_areas.serializers import GeographicalAreaSerializer


class GeoAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows geographical areas to be viewed.
    """

    queryset = GeographicalArea.objects.all().prefetch_related(
        "geographicalareadescription_set"
    )
    serializer_class = GeographicalAreaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "area_code"]


class GeoAreaUIViewSet(GeoAreaViewSet):
    """
    UI endpoint that allows geographical areas to be viewed.
    """

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request, "geo_areas/list.jinja", context={"object_list": queryset}
        )
