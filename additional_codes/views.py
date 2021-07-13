from typing import Type

from rest_framework import permissions
from rest_framework import viewsets

from additional_codes import business_rules
from additional_codes.filters import AdditionalCodeFilter
from additional_codes.filters import AdditionalCodeFilterBackend
from additional_codes.forms import AdditionalCodeCreateDescriptionForm
from additional_codes.forms import AdditionalCodeDescriptionForm
from additional_codes.forms import AdditionalCodeForm
from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeDescription
from additional_codes.models import AdditionalCodeType
from additional_codes.serializers import AdditionalCodeTypeSerializer
from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.views import BusinessRulesMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView
from workbaskets.views.generic import DraftUpdateView


class AdditionalCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows additional codes to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [AdditionalCodeFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            AdditionalCode.objects.approved_up_to_transaction(tx)
            .select_related("type")
            .prefetch_related("descriptions")
        )


class AdditionalCodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows additional code types to be viewed."""

    queryset = AdditionalCodeType.objects.latest_approved()
    serializer_class = AdditionalCodeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class AdditionalCodeMixin:
    model: Type[TrackedModel] = AdditionalCode

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return AdditionalCode.objects.approved_up_to_transaction(tx).select_related(
            "type",
        )


class AdditionalCodeCreateDescriptionMixin:
    model: Type[TrackedModel] = AdditionalCodeDescription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["described_object"] = AdditionalCode.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return context


class AdditionalCodeDescriptionMixin:
    model: Type[TrackedModel] = AdditionalCodeDescription

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return AdditionalCodeDescription.objects.approved_up_to_transaction(tx)


class AdditionalCodeList(AdditionalCodeMixin, TamatoListView):
    """UI endpoint for viewing and filtering Additional Codes."""

    template_name = "additional_codes/list.jinja"
    filterset_class = AdditionalCodeFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class AdditionalCodeDetail(AdditionalCodeMixin, TrackedModelDetailView):
    template_name = "additional_codes/detail.jinja"


class AdditionalCodeUpdate(
    AdditionalCodeMixin,
    BusinessRulesMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = AdditionalCodeForm

    validate_business_rules = (
        business_rules.ACN1,
        business_rules.ACN2,
        business_rules.ACN4,
        business_rules.ACN13,
        business_rules.ACN17,
        # business_rules.ACN5,  # XXX should it be checked here?
    )


class AdditionalCodeCreateDescription(
    AdditionalCodeCreateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftCreateView,
):
    def get_initial(self):
        initial = super().get_initial()
        initial["described_additionalcode"] = AdditionalCode.objects.get(
            sid=(self.kwargs.get("sid")),
        )
        return initial

    form_class = AdditionalCodeCreateDescriptionForm
    template_name = "common/create_description.jinja"


class AdditionalCodeUpdateDescription(
    AdditionalCodeDescriptionMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = AdditionalCodeDescriptionForm
    template_name = "common/edit_description.jinja"


class AdditionalCodeDescriptionConfirmCreate(
    AdditionalCodeDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"


class AdditionalCodeDescriptionConfirmUpdate(
    AdditionalCodeDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update_description.jinja"


class AdditionalCodeConfirmUpdate(AdditionalCodeMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"
