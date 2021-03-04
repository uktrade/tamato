from rest_framework import permissions
from rest_framework import viewsets

from additional_codes import models
from additional_codes.filters import AdditionalCodeFilter
from additional_codes.filters import AdditionalCodeFilterBackend
from additional_codes.forms import AdditionalCodeDescriptionForm
from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeType
from additional_codes.serializers import AdditionalCodeSerializer
from additional_codes.serializers import AdditionalCodeTypeSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailView
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftUpdateView


class AdditionalCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows additional codes to be viewed."""

    queryset = (
        AdditionalCode.objects.latest_approved()
        .select_related("type")
        .prefetch_related("descriptions")
    )
    serializer_class = AdditionalCodeSerializer
    filter_backends = [AdditionalCodeFilterBackend]
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class AdditionalCodeList(TamatoListView):
    """UI endpoint for viewing and filtering Additional Codes."""

    queryset = (
        models.AdditionalCode.objects.latest_approved()
        .select_related("type")
        .prefetch_related("descriptions")
    )
    template_name = "additional_codes/list.jinja"
    filterset_class = AdditionalCodeFilter
    search_fields = [
        "type__sid",
        "code",
        "sid",
        "descriptions__description",
    ]


class AdditionalCodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows additional code types to be viewed."""

    queryset = AdditionalCodeType.objects.latest_approved()
    serializer_class = AdditionalCodeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class AdditionalCodeDetail(TrackedModelDetailView):
    model = models.AdditionalCode
    template_name = "additional_codes/detail.jinja"
    queryset = (
        models.AdditionalCode.objects.latest_approved()
        .select_related("type")
        .prefetch_related("descriptions")
    )


class AdditionalCodeEditDescription(TrackedModelDetailView, DraftUpdateView):
    model = models.AdditionalCodeDescription
    template_name = "additional_codes/edit/description.jinja"
    form_class = AdditionalCodeDescriptionForm

    def get_queryset(self):
        return models.AdditionalCodeDescription.objects.approved_up_to_transaction(
            WorkBasket.current(self.request).transactions.order_by("pk").last(),
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = kwargs.get("instance")
        if self.request.method == "POST" and instance:
            kwargs["instance"] = instance.new_draft(
                WorkBasket.current(self.request),
                save=False,
            )
        return kwargs

    def get_success_url(self):
        return reverse(
            "additional_code-ui-confirm-description-update",
            kwargs=self.kwargs,
        )


class AdditionalCodeConfirmDescriptionUpdate(TrackedModelDetailView):
    model = models.AdditionalCodeDescription
    template_name = "additional_codes/confirm_update.jinja"

    def get_queryset(self):
        return models.AdditionalCodeDescription.objects.approved_up_to_transaction(
            WorkBasket.current(self.request).transactions.order_by("pk").last(),
        )
