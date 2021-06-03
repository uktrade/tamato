from typing import Type

from rest_framework import permissions
from rest_framework import viewsets

from common.models.records import TrackedModel
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from geo_areas.filters import GeographicalAreaFilter
from geo_areas.forms import GeographicalAreaCreateDescriptionForm
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.serializers import GeographicalAreaSerializer
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView


class GeoAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows geographical areas to be viewed."""

    queryset = GeographicalArea.objects.latest_approved().prefetch_related(
        "descriptions",
    )
    serializer_class = GeographicalAreaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "area_code"]


class GeographicalAreaDescriptionMixin:
    model: Type[TrackedModel] = GeographicalAreaDescription

    def get_queryset(self):
        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        return GeographicalAreaDescription.objects.approved_up_to_transaction(tx)


class GeographicalAreaCreateDescriptionMixin:
    model: Type[TrackedModel] = GeographicalAreaDescription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["described_object"] = GeographicalArea.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return context


class GeographicalAreaList(TamatoListView):
    queryset = GeographicalArea.objects.latest_approved()
    template_name = "geo_areas/list.jinja"
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "descriptions__description"]


class GeographicalAreaDetail(TrackedModelDetailView):
    model = GeographicalArea
    template_name = "geo_areas/detail.jinja"
    queryset = GeographicalArea.objects.latest_approved()


class GeographicalAreaCreateDescription(
    GeographicalAreaCreateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftCreateView,
):
    def get_initial(self):
        initial = super().get_initial()
        initial["described_geographicalarea"] = GeographicalArea.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return initial

    form_class = GeographicalAreaCreateDescriptionForm
    template_name = "common/create_description.jinja"


class GeographicalAreaDescriptionConfirmCreate(
    GeographicalAreaDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"
