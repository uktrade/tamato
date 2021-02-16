from rest_framework import permissions
from rest_framework import viewsets

from additional_codes import models
from additional_codes.filters import AdditionalCodeFilter
from additional_codes.filters import AdditionalCodeFilterBackend
from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from additional_codes.serializers import AdditionalCodeSerializer
from additional_codes.serializers import AdditionalCodeTypeSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailView


class AdditionalCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows additional codes to be viewed."""

    queryset = (
        AdditionalCode.objects.current()
        .select_related("type")
        .prefetch_related("descriptions")
    )
    serializer_class = AdditionalCodeSerializer
    filter_backends = [AdditionalCodeFilterBackend]
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class AdditionalCodeList(TamatoListView):
    """UI endpoint for viewing and filtering Additional Codes."""

    queryset = (
        models.AdditionalCode.objects.current()
        .select_related("type")
        .prefetch_related("descriptions")
    )
    template_name = "additional_codes/list.jinja"
    filterset_class = AdditionalCodeFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class AdditionalCodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows additional code types to be viewed."""

    queryset = AdditionalCodeType.objects.current()
    serializer_class = AdditionalCodeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class AdditionalCodeDetail(TrackedModelDetailView):
    model = models.AdditionalCode
    template_name = "additional_codes/detail.jinja"
    queryset = (
        models.AdditionalCode.objects.current()
        .select_related("type")
        .prefetch_related("descriptions")
    )
