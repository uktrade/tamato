from typing import Type

from rest_framework import permissions
from rest_framework import viewsets

from common.models.trackedmodel import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from geo_areas import business_rules
from geo_areas import forms
from geo_areas.filters import GeographicalAreaFilter
from geo_areas.forms import GeographicalAreaCreateDescriptionForm
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView
from workbaskets.views.generic import DraftDeleteView


class GeoAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows geographical areas to be viewed."""

    queryset = (
        GeographicalArea.objects.latest_approved()
        .with_latest_description()
        .prefetch_related(
            "descriptions",
        )
    )

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = GeographicalAreaFilter
    search_fields = ["sid", "area_code"]


class GeoAreaMixin:
    model: Type[TrackedModel] = GeographicalArea

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return GeographicalArea.objects.approved_up_to_transaction(tx)


class GeoAreaDescriptionMixin:
    model: Type[TrackedModel] = GeographicalAreaDescription

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return GeographicalAreaDescription.objects.approved_up_to_transaction(tx)


class GeoAreaCreateDescriptionMixin:
    model: Type[TrackedModel] = GeographicalAreaDescription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["described_object"] = GeographicalArea.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return context


class GeoAreaList(GeoAreaMixin, TamatoListView):
    template_name = "geo_areas/list.jinja"
    filterset_class = GeographicalAreaFilter
    filterset_class.search_fields = ["area_id", "description"]

    def get_queryset(self):
        return GeographicalArea.objects.current().with_current_descriptions()


class GeoAreaDetail(GeoAreaMixin, TrackedModelDetailView):
    template_name = "geo_areas/detail.jinja"


class GeoAreaDelete(GeoAreaMixin, TrackedModelDetailMixin, DraftDeleteView):
    form_class = forms.GeographicalAreaDeleteForm
    success_path = "list"

    validate_business_rules = (
        business_rules.GA21,
        business_rules.GA22,
    )


class GeoAreaDescriptionCreate(
    GeoAreaCreateDescriptionMixin,
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


class GeoAreaDescriptionConfirmCreate(
    GeoAreaDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"


class GeoAreaDescriptionDelete(
    GeoAreaDescriptionMixin,
    TrackedModelDetailMixin,
    DraftDeleteView,
):
    form_class = forms.GeographicalAreaDescriptionDeleteForm
    success_path = "detail"
