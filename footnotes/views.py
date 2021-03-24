from typing import Optional
from typing import Type

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Model
from django.db.models import QuerySet
from django.http import Http404
from django.views.generic import DetailView
from rest_framework import permissions
from rest_framework import viewsets

from common.models import TrackedModel
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from footnotes import forms
from footnotes import models
from footnotes.filters import FootnoteFilter
from footnotes.filters import FootnoteFilterBackend
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftUpdateView
from workbaskets.views.mixins import WithCurrentWorkBasket


class FootnoteViewSet(viewsets.ModelViewSet):
    """API endpoint that allows footnotes to be viewed and edited."""

    queryset = (
        models.Footnote.objects.latest_approved()
        .select_related("footnote_type")
        .prefetch_related("descriptions")
    )
    serializer_class = FootnoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [FootnoteFilterBackend]
    search_fields = [
        "footnote_id",
        "footnote_type__footnote_type_id",
        "descriptions__description",
        "footnote_type__description",
    ]


class FootnoteMixin:
    model: Type[TrackedModel] = models.Footnote

    def get_queryset(self):
        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        return models.Footnote.objects.approved_up_to_transaction(tx).select_related(
            "footnote_type",
        )


class FootnoteList(FootnoteMixin, TamatoListView):
    """UI endpoint for viewing and filtering Footnotes."""

    template_name = "footnotes/list.jinja"
    filterset_class = FootnoteFilter
    search_fields = [
        "footnote_id",
        "footnote_type__footnote_type_id",
        "descriptions__description",
        "footnote_type__description",
    ]


class FootnoteDetail(FootnoteMixin, TrackedModelDetailView):
    template_name = "footnotes/detail.jinja"


class FootnoteUpdate(
    PermissionRequiredMixin,
    FootnoteMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.FootnoteForm
    permission_required = "common.change_trackedmodel"

    def get_object(self, queryset: Optional[QuerySet] = None) -> Model:
        obj = super().get_object(queryset)

        if self.request.method == "POST":
            obj = obj.new_draft(
                WorkBasket.current(self.request),
                save=False,
            )

        return obj


class FootnoteConfirmUpdate(FootnoteMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class FootnoteDescriptionMixin:
    required_url_kwargs = [
        "described_footnote__footnote_type__footnote_type_id",
        "described_footnote__footnote_id",
        "description_period_sid",
    ]

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        if not all(key in self.kwargs for key in self.required_url_kwargs):
            raise AttributeError(
                f"{self.__class__.__name__} must be called with a footnote type id, a "
                f"footnote id, and a period sid in the URLconf.",
            )

        queryset = queryset.filter(**self.kwargs)

        try:
            return queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(f"No footnote description matching the query")


class FootnoteDescriptionUpdate(FootnoteDescriptionMixin, DraftUpdateView):
    form_class = forms.FootnoteDescriptionForm
    queryset = models.FootnoteDescription.objects.latest_approved()
    template_name = "footnotes/edit_description.jinja"

    def get_success_url(self):
        return self.object.get_url("confirm-update")


class FootnoteDescriptionConfirmUpdate(
    WithCurrentWorkBasket,
    FootnoteDescriptionMixin,
    DetailView,
):
    queryset = models.FootnoteDescription.objects.latest_approved()
    template_name = "footnotes/confirm_update_description.jinja"


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows footnote types to be viewed or edited."""

    queryset = models.FootnoteType.objects.latest_approved()
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
