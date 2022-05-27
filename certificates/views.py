from typing import Type

from django.db import transaction
from rest_framework import permissions
from rest_framework import viewsets

from certificates import business_rules
from certificates import forms
from certificates import models
from certificates.filters import CertificateFilter
from certificates.filters import CertificateFilterBackend
from certificates.serializers import CertificateTypeSerializer
from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView
from workbaskets.views.generic import DraftDeleteView
from workbaskets.views.generic import DraftUpdateView


class CertificatesViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows certificates to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [CertificateFilterBackend]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            models.Certificate.objects.approved_up_to_transaction(tx)
            .select_related("certificate_type")
            .prefetch_related("descriptions")
        )


class CertificateTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows certificate types to be viewed."""

    queryset = models.CertificateType.objects.all()
    serializer_class = CertificateTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class CertificateMixin:
    model: Type[TrackedModel] = models.Certificate

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.Certificate.objects.approved_up_to_transaction(tx).select_related(
            "certificate_type",
        )


class CertificateList(CertificateMixin, TamatoListView):
    """UI endpoint for viewing and filtering Certificates."""

    template_name = "certificates/list.jinja"
    filterset_class = CertificateFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class CertificateCreate(DraftCreateView):
    """UI endpoint for creating Certificates."""  # /PS-IGNORE

    template_name = "certificates/create.jinja"
    form_class = forms.CertificateCreateForm

    @transaction.atomic
    def form_valid(self, form):
        transaction = self.get_transaction()
        transaction.save()
        self.object = form.save(commit=False)
        self.object.update_type = UpdateType.CREATE
        self.object.transaction = transaction
        self.object.save()

        description = form.cleaned_data["certificate_description"]
        description.described_certificate = self.object
        description.update_type = UpdateType.CREATE
        description.transaction = transaction
        description.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class CertificateConfirmCreate(CertificateMixin, TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"


class CertificateDetail(CertificateMixin, TrackedModelDetailView):
    template_name = "certificates/detail.jinja"


class CertificateUpdate(
    CertificateMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.CertificateForm

    validate_business_rules = (
        business_rules.CE2,
        business_rules.CE4,
        # business_rules.CE6,  # XXX should it be checked here?
        business_rules.CE7,
    )


class CertificateConfirmUpdate(CertificateMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class CertificateDescriptionMixin:
    model: Type[TrackedModel] = models.CertificateDescription

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.CertificateDescription.objects.approved_up_to_transaction(tx)


class CertificateCreateDescriptionMixin:
    model: Type[TrackedModel] = models.CertificateDescription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["described_object"] = models.Certificate.objects.get(
            certificate_type__sid=(self.kwargs.get("certificate_type__sid")),
            sid=(self.kwargs.get("sid")),
        )
        return context


class CertificateDescriptionCreate(
    CertificateCreateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftCreateView,
):
    def get_initial(self):
        initial = super().get_initial()
        initial["described_certificate"] = models.Certificate.objects.get(
            certificate_type__sid=(self.kwargs.get("certificate_type__sid")),
            sid=(self.kwargs.get("sid")),
        )
        return initial

    form_class = forms.CertificateCreateDescriptionForm
    template_name = "common/create_description.jinja"


class CertificateUpdateDescription(
    CertificateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.CertificateDescriptionForm
    template_name = "common/edit_description.jinja"


class CertificateDescriptionConfirmCreate(
    CertificateDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"


class CertificateDescriptionConfirmUpdate(
    CertificateDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update_description.jinja"


class CertificateDelete(
    CertificateMixin,
    TrackedModelDetailMixin,
    DraftDeleteView,
):
    form_class = forms.CertificateDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.CE5,)


class CertificateDescriptionDelete(
    CertificateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftDeleteView,
):
    form_class = forms.CertificateDescriptionDeleteForm
    success_path = "detail"
