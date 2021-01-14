from django.shortcuts import render
from django.core.paginator import Paginator
from django.conf import settings
from rest_framework import permissions
from rest_framework import viewsets


from additional_codes.filters import AdditionalCodeFilterBackend
from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from additional_codes.serializers import AdditionalCodeSerializer
from additional_codes.serializers import AdditionalCodeTypeSerializer

from common.pagination import build_pagination_list


class AdditionalCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows additional codes to be viewed.
    """

    queryset = (
        AdditionalCode.objects.current()
        .select_related("type")
        .prefetch_related("descriptions")
    )
    serializer_class = AdditionalCodeSerializer
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
        paginator = Paginator(queryset, settings.REST_FRAMEWORK["PAGE_SIZE"])

        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        page_obj.page_links = build_pagination_list(
            int(page_number), page_obj.paginator.num_pages
        )

        return render(
            request, "additional_codes/list.jinja", context={"object_list": page_obj}
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
