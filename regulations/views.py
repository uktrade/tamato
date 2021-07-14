from django.http.response import HttpResponseRedirect
from rest_framework import viewsets

from common.serializers import AutoCompleteSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailView
from regulations.filters import RegulationFilter
from regulations.filters import RegulationFilterBackend
from regulations.forms import RegulationCreateForm
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView


class RegulationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows regulations to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [RegulationFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Regulation.objects.approved_up_to_transaction(tx).select_related(
            "regulation_group",
        )


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
        transaction = self.get_transaction()
        transaction.save()
        # CreateView.get_success_url() override relies upon a valid self.object.
        self.object = form.save(commit=False)
        self.object.update_type = self.UPDATE_TYPE
        self.object.transaction = transaction
        self.object.save()
        # Tamato's CreateView.get_success_url() relies upon Regulation's base
        # class generating URLs for the main views.
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Make the request available to the form allowing transaction management
        # from the form.
        kwargs["request"] = self.request
        return kwargs

class RegulationConfirmCreate(TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"
    model = Regulation

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Regulation.objects.approved_up_to_transaction(tx)
