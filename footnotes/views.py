from typing import Type

from rest_framework import permissions
from rest_framework import viewsets

from common.models import TrackedModel
from common.views import BusinessRulesMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from footnotes import business_rules
from footnotes import forms
from footnotes import models
from footnotes.filters import FootnoteFilter
from footnotes.filters import FootnoteFilterBackend
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftCreateView
from workbaskets.views.generic import DraftUpdateView


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


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows footnote types to be viewed or edited."""

    queryset = models.FootnoteType.objects.latest_approved()
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


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


class FootnoteDescriptionMixin:
    model: Type[TrackedModel] = models.FootnoteDescription

    def get_queryset(self):
        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        return models.FootnoteDescription.objects.approved_up_to_transaction(tx)


class FootnoteCreateDescriptionMixin:
    model: Type[TrackedModel] = models.FootnoteDescription

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["described_object"] = models.Footnote.objects.get(
            footnote_type__footnote_type_id=(
                self.kwargs.get("footnote_type__footnote_type_id")
            ),
            footnote_id=(self.kwargs.get("footnote_id")),
        )
        return context


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
    FootnoteMixin,
    BusinessRulesMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.FootnoteForm

    validate_business_rules = (
        business_rules.FO2,
        # business_rules.FO4,  # XXX should it be checked here?
        business_rules.FO5,
        business_rules.FO6,
        business_rules.FO9,
        business_rules.FO17,
    )


class FootnoteConfirmUpdate(FootnoteMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class FootnoteCreateDescription(
    FootnoteCreateDescriptionMixin,
    TrackedModelDetailMixin,
    DraftCreateView,
):
    def get_initial(self):
        initial = super().get_initial()
        initial["described_footnote"] = models.Footnote.objects.get(
            footnote_type__footnote_type_id=(
                self.kwargs.get("footnote_type__footnote_type_id")
            ),
            footnote_id=(self.kwargs.get("footnote_id")),
        )
        return initial

    form_class = forms.FootnoteCreateDescriptionForm
    template_name = "common/create_description.jinja"


class FootnoteUpdateDescription(
    FootnoteDescriptionMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.FootnoteDescriptionForm
    template_name = "common/edit_description.jinja"


class FootnoteDescriptionConfirmCreate(
    FootnoteDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"


class FootnoteDescriptionConfirmUpdate(
    FootnoteDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update_description.jinja"
