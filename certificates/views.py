from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models
from rest_framework import permissions
from rest_framework import viewsets

from certificates.filters import CertificateFilter
from certificates.forms import CertificateForm
from certificates.models import Certificate
from certificates.models import CertificateType
from certificates.serializers import CertificateSerializer
from certificates.serializers import CertificateTypeSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftUpdateView


class CertificatesViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows certificates to be viewed."""

    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "code"]


class CertificateTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows certificate types to be viewed."""

    queryset = CertificateType.objects.all()
    serializer_class = CertificateTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class CertificatesList(TamatoListView):
    """UI endpoint for viewing and filtering Certificates."""

    queryset = Certificate.objects.latest_approved().select_related("certificate_type")
    template_name = "certificates/list.jinja"
    filterset_class = CertificateFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class CertificateDetailMixin:
    model: type[models.Model] = Certificate

    def get_queryset(self):
        return Certificate.objects.approved_up_to_transaction(
            WorkBasket.current(self.request).transactions.order_by("order").last(),
        ).select_related("certificate_type")


class CertificateDetail(CertificateDetailMixin, TrackedModelDetailView):
    template_name = "certificates/detail.jinja"


class CertificateUpdate(
    PermissionRequiredMixin,
    CertificateDetailMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = CertificateForm
    permission_required = "common.change_trackedmodel"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = kwargs.get("instance")
        if self.request.method == "POST" and instance:
            kwargs["instance"] = instance.new_draft(
                WorkBasket.current(self.request),
                save=False,
            )
        kwargs["initial"].update(
            {
                "code": instance.code,
                "certificate_type": instance.certificate_type_id,
            },
        )
        return kwargs


class CertificateConfirmUpdate(CertificateDetailMixin, TrackedModelDetailView):
    template_name = "certificates/confirm_update.jinja"
