from typing import Type

from rest_framework import permissions
from rest_framework import viewsets

from certificates import forms
from certificates import models
from certificates.filters import CertificateFilter
from certificates.serializers import CertificateSerializer
from certificates.serializers import CertificateTypeSerializer
from common.models import TrackedModel
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftUpdateView


class CertificatesViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows certificates to be viewed."""

    queryset = models.Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "code"]


class CertificateTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows certificate types to be viewed."""

    queryset = models.CertificateType.objects.all()
    serializer_class = CertificateTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class CertificateMixin:
    model: Type[TrackedModel] = models.Certificate

    def get_queryset(self):
        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        return models.Certificate.objects.approved_up_to_transaction(tx).select_related(
            "certificate_type",
        )


class CertificatesList(CertificateMixin, TamatoListView):
    """UI endpoint for viewing and filtering Certificates."""

    template_name = "certificates/list.jinja"
    filterset_class = CertificateFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class CertificateDetail(CertificateMixin, TrackedModelDetailView):
    template_name = "certificates/detail.jinja"


class CertificateUpdate(
    CertificateMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.CertificateForm


class CertificateConfirmUpdate(CertificateMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class CertificateDescriptionMixin:
    model: Type[TrackedModel] = models.CertificateDescription

    def get_queryset(self):
        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        return models.CertificateDescription.objects.approved_up_to_transaction(tx)


class CertificateUpdateDescription(
    CertificateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.CertificateDescriptionForm
    template_name = "common/edit_description.jinja"


class CertificateDescriptionConfirmUpdate(
    CertificateDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update_description.jinja"
