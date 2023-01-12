from datetime import date
from urllib.parse import urlencode

from django.urls import reverse
from django.views.generic.list import ListView
from rest_framework import permissions
from rest_framework import viewsets

from common.serializers import AutoCompleteSerializer
from common.views import SortingMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures.models import Measure
from quotas import business_rules
from quotas import forms
from quotas import models
from quotas import serializers
from quotas.filters import OrderNumberFilterBackend
from quotas.filters import QuotaFilter
from quotas.models import QuotaBlocking
from quotas.models import QuotaSuspension
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricDeleteView


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
    """Returns a list of QuotaOrderNumber objects."""

    template_name = "quotas/list.jinja"
    filterset_class = QuotaFilter


class QuotaDetail(QuotaMixin, TrackedModelDetailView):
    template_name = "quotas/detail.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        definitions = self.object.definitions.current()
        current_definition = definitions.as_at_and_beyond(date.today()).first()
        context["current_definition"] = current_definition

        context["blocking_period"] = (
            QuotaBlocking.objects.filter(quota_definition=current_definition)
            .as_at_and_beyond(date.today())
            .first()
        )

        context["suspension_period"] = (
            QuotaSuspension.objects.filter(quota_definition=current_definition)
            .as_at_and_beyond(date.today())
            .first()
        )

        context["measures"] = Measure.objects.filter(order_number=self.object).as_at(
            date.today(),
        )
        url_params = urlencode({"order_number": self.object.pk})
        context["measures_url"] = f"{reverse('measure-ui-list')}?{url_params}"

        return context


class QuotaDefinitionList(SortingMixin, ListView):
    template_name = "quotas/definitions.jinja"
    model = models.QuotaDefinition
    sort_by_fields = ["sid", "valid_between"]

    def get_queryset(self):
        self.queryset = models.QuotaDefinition.objects.current().filter(
            order_number=self.quota,
        )
        return super().get_queryset()

    @property
    def quota(self):
        return models.QuotaOrderNumber.objects.get(sid=self.kwargs["sid"])

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(quota=self.quota, *args, **kwargs)


class QuotaDelete(QuotaMixin, TrackedModelDetailMixin, CreateTaricDeleteView):
    form_class = forms.QuotaDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.ON11,)
