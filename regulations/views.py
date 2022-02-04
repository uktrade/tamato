from typing import Type

from rest_framework import viewsets

from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from regulations import business_rules
from regulations.filters import RegulationFilter
from regulations.filters import RegulationFilterBackend
from regulations.forms import RegulationCreateForm
from regulations.forms import RegulationEditForm
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView
from workbaskets.views.generic import DraftUpdateView


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


class RegulationMixin:
    model: Type[TrackedModel] = Regulation

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Regulation.objects.approved_up_to_transaction(tx).select_related(
            "regulation_group",
        )


class RegulationDetail(RegulationMixin, TrackedModelDetailView):
    required_url_kwargs = ("regulation_id",)
    template_name = "regulations/detail.jinja"


class RegulationCreate(DraftCreateView):
    """UI to create new regulations."""

    template_name = "regulations/create.jinja"
    form_class = RegulationCreateForm

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


class RegulationUpdate(
    RegulationMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    template_name = "regulations/edit.jinja"
    form_class = RegulationEditForm
    validate_business_rules = (
        business_rules.ROIMB1,
        business_rules.ROIMB4,
        business_rules.ROIMB8,
        business_rules.ROIMB44,
        business_rules.ROIMB47,
    )


class RegulationConfirmUpdate(
    RegulationMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update.jinja"
