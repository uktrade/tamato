from django.http.response import HttpResponseRedirect
from rest_framework import viewsets

from common.views import TamatoListView
from common.views import TrackedModelDetailView
from regulations.filters import RegulationFilter
from regulations.filters import RegulationFilterBackend
from regulations.forms import RegulationCreateForm
from regulations.models import Regulation
from regulations.serializers import RegulationSerializer
from workbaskets.views.generic import DraftCreateView


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

    model = Regulation
    template_name = "regulations/detail.jinja"
    queryset = Regulation.objects.latest_approved().select_related("regulation_group")


class RegulationCreate(DraftCreateView):
    template_name = "regulations/create.jinja"
    form_class = RegulationCreateForm

    def form_valid(self, form):
        return HttpResponseRedirect(self.get_success_url())


class RegulationConfirmCreate(TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"
