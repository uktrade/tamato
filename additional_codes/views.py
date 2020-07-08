from django.shortcuts import render
from rest_framework import permissions
from rest_framework import viewsets

from additional_codes.filters import AdditionalCodeFilterBackend
from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from additional_codes.serializers import AdditionalCodeSerializer
from additional_codes.serializers import AdditionalCodeTypeSerializer


class AdditionalCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows additional codes to be viewed.
    """

    queryset = AdditionalCode.objects.all().prefetch_related("descriptions")
    serializer_class = AdditionalCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [AdditionalCodeFilterBackend]
    search_fields = [
        "sid",
        "code",
        "descriptions__description",
        "type__sid",
        "type__description",
    ]


class AdditionalCodeUIViewSet(AdditionalCodeViewSet):
    """
    UI endpoint that allows additional codes to be viewed.
    """

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request, "additional_codes/list.jinja", context={"object_list": queryset}
        )

    def retrieve(self, request, *args, **kwargs):
        return render(
            request,
            "additional_codes/detail.jinja",
            context={"object": self.get_object()},
        )


class AdditionalCodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows additional code types to be viewed.
    """

    queryset = AdditionalCodeType.objects.all()
    serializer_class = AdditionalCodeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
