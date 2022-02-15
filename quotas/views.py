from rest_framework import permissions
from rest_framework import viewsets

from common.serializers import AutoCompleteSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from quotas import business_rules
from quotas import forms
from quotas import models
from quotas import serializers
from quotas.filters import OrderNumberFilterBackend
from quotas.filters import QuotaFilter
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftDeleteView


class QuotaOrderNumberViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows quota order numbers to be viewed."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderNumberFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaOrderNumberOriginViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOrigin.objects.has_approved_state()
    serializer_class = serializers.QuotaOrderNumberOriginSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaOrderNumberOriginExclusionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOriginExclusion.objects.has_approved_state()
    serializer_class = serializers.QuotaOrderNumberOriginExclusionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaDefinitionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaDefinition.objects.has_approved_state()
    serializer_class = serializers.QuotaDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "order_number__order_number", "description"]


class QuotaAssociationViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaAssociation.objects.has_approved_state()
    serializer_class = serializers.QuotaAssociationSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaSuspensionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaSuspension.objects.has_approved_state()
    serializer_class = serializers.QuotaSuspensionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaBlockingViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaBlocking.objects.has_approved_state()
    serializer_class = serializers.QuotaBlockingSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaEventViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaEvent.objects.has_approved_state()
    serializer_class = serializers.QuotaEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaMixin:
    model = models.QuotaOrderNumber

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaList(QuotaMixin, TamatoListView):
    template_name = "quotas/list.jinja"
    filterset_class = QuotaFilter


class QuotaDetail(QuotaMixin, TrackedModelDetailView):
    template_name = "quotas/detail.jinja"


class QuotaDelete(QuotaMixin, TrackedModelDetailMixin, DraftDeleteView):
    form_class = forms.QuotaDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.ON11,)
