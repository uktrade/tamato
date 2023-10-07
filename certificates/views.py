from typing import Type
from urllib.parse import urlencode

from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView
from rest_framework import permissions
from rest_framework import viewsets

from certificates import business_rules
from certificates import forms
from certificates import models
from certificates.filters import CertificateFilter
from certificates.filters import CertificateFilterBackend
from certificates.models import Certificate
from certificates.serializers import CertificateTypeSerializer
from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.validators import UpdateType
from common.views import DescriptionDeleteMixin
from common.views import SortingMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from common.views import WithPaginationListMixin
from measures.models import Measure
from measures.models import MeasureCondition
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


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


class CertificateCreate(CreateTaricCreateView):
    """UI endpoint for creating Certificates CREATE instances."""

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

        return super().form_valid(form)

    @transaction.atomic
    def get_result_object(self, form):
        object = super().get_result_object(form)
        description = form.cleaned_data["certificate_description"]
        description.described_certificate = self.object
        description.update_type = UpdateType.CREATE
        description.transaction = object.transaction
        description.save()

        return object

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class CertificateEditCreate(
    CertificateMixin,  # Sets model and defines get_queryset()
    TrackedModelDetailMixin,  # Defines get_object()
    EditTaricView,  # Overrides get_result_object() which normally creates new version.
):
    """UI endpoint for editing Certificate CREATE instances."""

    template_name = "certificates/create.jinja"
    form_class = forms.CertificateEditCreateForm

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class CertificateConfirmCreate(CertificateMixin, TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"


class CertificateDetail(CertificateMixin, TrackedModelDetailView):
    template_name = "certificates/detail.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["selected_tab"] = "details"
        return context


class CertificateDetailDescriptions(CertificateDetail):
    """Displays descriptions for a certificate as a simulated tab on certificate
    view."""

    template_name = "includes/certificates/tabs/descriptions.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["selected_tab"] = "descriptions"
        return context


class CertificateDetailVersionControl(CertificateDetail):
    """Displays version history for a certificate as a simulated tab on
    certificate view."""

    template_name = "includes/certificates/tabs/version_control.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["selected_tab"] = "version-control"
        return context


class CertificateDetailMeasures(SortingMixin, WithPaginationListMixin, ListView):
    """Displays a pagination list of measures for a certificate as a simulated
    tab on certificate view."""

    model = Measure
    template_name = "includes/certificates/tabs/measures.jinja"
    paginate_by = 20
    sort_by_fields = ["goods_nomenclature", "start_date"]
    custom_sorting = {
        "start_date": "valid_between",
    }

    @property
    def certificate(self):
        return Certificate.objects.current().get(
            sid=self.kwargs["sid"],
            certificate_type__sid=self.kwargs["certificate_type__sid"],
        )

    def get_queryset(self):
        measure_ids = MeasureCondition.objects.filter(
            required_certificate=self.certificate.trackedmodel_ptr_id,
        ).values_list("dependent_measure_id", flat=True)
        queryset = Measure.objects.all().current().filter(id__in=measure_ids)
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["object"] = self.certificate
        context["selected_tab"] = "measures"
        url_params = urlencode({"certificates": self.certificate.pk})
        measures_url = f"{reverse('measure-ui-list')}?{url_params}"
        context["measures_url"] = measures_url
        return context


class CertificateUpdateMixin(
    CertificateMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.CertificateForm

    validate_business_rules = (
        business_rules.CE2,
        business_rules.CE4,
        # business_rules.CE6,  # XXX should it be checked here?
        business_rules.CE7,
    )


class CertificateUpdate(
    CertificateUpdateMixin,
    CreateTaricUpdateView,
):
    """UI endpoint for creating Certificate UPDATE instances."""


class CertificateEditUpdate(
    CertificateUpdateMixin,
    EditTaricView,
):
    """UI endpoint for editing Certificate UPDATE instances."""


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
        context["described_object"] = models.Certificate.objects.current().get(
            certificate_type__sid=(self.kwargs.get("certificate_type__sid")),
            sid=(self.kwargs.get("sid")),
        )
        return context


class CertificateDescriptionCreate(
    CertificateCreateDescriptionMixin,
    TrackedModelDetailMixin,
    CreateTaricCreateView,
):
    """UI endpoint for creating CertificateDescription CREATE instances."""

    def get_initial(self):
        initial = super().get_initial()
        initial["described_certificate"] = models.Certificate.objects.current().get(
            certificate_type__sid=(self.kwargs.get("certificate_type__sid")),
            sid=(self.kwargs.get("sid")),
        )
        return initial

    form_class = forms.CertificateCreateDescriptionForm
    template_name = "common/create_description.jinja"


class CertificateDescriptionEditCreate(
    CertificateDescriptionMixin,
    TrackedModelDetailMixin,
    EditTaricView,
):
    """UI endpoint for editing CertificateDescription CREATE instances."""

    form_class = forms.CertificateDescriptionForm
    template_name = "common/edit_description.jinja"

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())


class CertificateUpdateDescription(
    CertificateDescriptionMixin,
    TrackedModelDetailMixin,
    CreateTaricUpdateView,
):
    """UI endpoint for creating CertificateDescription UPDATE instances."""

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
    CreateTaricDeleteView,
):
    form_class = forms.CertificateDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.CE5,)


class CertificateDescriptionDelete(
    CertificateDescriptionMixin,
    DescriptionDeleteMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.CertificateDescriptionDeleteForm
    success_path = "detail"
