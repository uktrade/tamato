from django.shortcuts import render
from rest_framework import permissions
from rest_framework import viewsets

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


class GeoAreaUIViewSet(GeoAreaViewSet):
    """
    UI endpoint that allows geographical areas to be viewed.
    """

    def list(self, request, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request, "geo_areas/list.jinja", context={"object_list": queryset}
        )

    def retrieve(self, request, *args, **kwargs):
        area = self.get_object()

        is_group = area.area_code == 1
        kwargs = {"geo_group": area} if is_group else {"member": area}

        return render(
            request,
            "geo_areas/detail.jinja",
            context={
                "area": area,
                "is_group": is_group,
                "members": GeographicalMembership.objects.current().filter(**kwargs),
            },
        )
