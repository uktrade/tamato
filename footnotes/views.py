from typing import Type

from django.db import transaction
from django.http import HttpResponseRedirect
from rest_framework import permissions
from rest_framework import viewsets

from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from footnotes import business_rules
from footnotes import forms
from footnotes import models
from footnotes.filters import FootnoteFilter
from footnotes.filters import FootnoteFilterBackend
from footnotes.serializers import FootnoteTypeSerializer
from workbaskets.models import WorkBasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


class FootnoteViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows footnotes to be viewed and edited."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [FootnoteFilterBackend]
    search_fields = [
        "footnote_id",
        "footnote_type__footnote_type_id",
        "descriptions__description",
        "footnote_type__description",
    ]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            models.Footnote.objects.approved_up_to_transaction(tx)
            .select_related("footnote_type")
            .prefetch_related("descriptions")
        )


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows footnote types to be viewed or edited."""

    # Since the introduction of the current_objects ModelManager instance on
    # TrackedModel, View.queryset can be better expressed as:
    # queryset = models.FootnoteType.current_objects
    queryset = models.FootnoteType.objects.latest_approved()
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class FootnoteMixin:
    model: Type[TrackedModel] = models.Footnote

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.Footnote.objects.approved_up_to_transaction(tx).select_related(
            "footnote_type",
        )


class FootnoteDescriptionMixin:
    model: Type[TrackedModel] = models.FootnoteDescription

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
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


class FootnoteCreate(CreateTaricCreateView):
    """UI endpoint for creating Footnote CREATE instances."""

    template_name = "footnotes/create.jinja"
    form_class = forms.FootnoteCreateForm

    @transaction.atomic
    def form_valid(self, form):
        transaction = self.get_transaction()
        transaction.save()
        self.object = form.save(commit=False)
        self.object.update_type = UpdateType.CREATE
        self.object.transaction = transaction
        self.object.save()

        description = form.cleaned_data["footnote_description"]
        description.described_footnote = self.object
        description.update_type = UpdateType.CREATE
        description.transaction = transaction
        description.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class FootnoteEditCreate(
    FootnoteMixin,
    TrackedModelDetailMixin,
    EditTaricView,
):
    """UI endpoint for editing Footnote CREATE instances."""

    template_name = "footnotes/create.jinja"
    form_class = forms.FootnoteEditCreateForm

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class FootnoteConfirmCreate(FootnoteMixin, TrackedModelDetailView):
    template_name = "common/confirm_create.jinja"


class FootnoteDetail(FootnoteMixin, TrackedModelDetailView):
    template_name = "footnotes/detail.jinja"


class FootnoteUpdateMixin(
    FootnoteMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.FootnoteForm

    validate_business_rules = (
        business_rules.FO2,
        business_rules.FO4,
        business_rules.FO5,
        business_rules.FO6,
        business_rules.FO9,
        business_rules.FO17,
    )


class FootnoteUpdate(
    FootnoteUpdateMixin,
    CreateTaricUpdateView,
):
    """UI endpoint for creating Footnote UPDATE instances."""


class FootnoteEditUpdate(
    FootnoteUpdateMixin,
    EditTaricView,
):
    """UI endpoint for editing Footnote UPDATE instances."""


class FootnoteConfirmUpdate(FootnoteMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


class FootnoteDelete(
    FootnoteMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.FootnoteDeleteForm
    success_path = "list"

    validate_business_rules = (
        business_rules.FO11,
        business_rules.FO12,
        business_rules.FO15,
    )


class FootnoteDescriptionCreate(
    FootnoteCreateDescriptionMixin,
    TrackedModelDetailMixin,
    CreateTaricCreateView,
):
    """UI endpoint for creating FootnoteDescription CREATE instances."""

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


class FootnoteDescriptionUpdate(
    FootnoteDescriptionMixin,
    TrackedModelDetailMixin,
    CreateTaricUpdateView,
):
    """UI endpoint for creating FootnoteDescription UPDATE instances."""

    form_class = forms.FootnoteDescriptionForm
    template_name = "common/edit_description.jinja"


class FootnoteDescriptionConfirmCreate(
    FootnoteDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_create_description.jinja"


class FootnoteDescriptionEditCreate(
    FootnoteDescriptionMixin,
    TrackedModelDetailMixin,
    EditTaricView,
):
    """UI endpoint for editing FootnoteDescription CREATE instances."""

    form_class = forms.FootnoteDescriptionForm
    template_name = "common/edit_description.jinja"

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())


class FootnoteDescriptionConfirmUpdate(
    FootnoteDescriptionMixin,
    TrackedModelDetailView,
):
    template_name = "common/confirm_update_description.jinja"


class FootnoteDescriptionDelete(
    FootnoteDescriptionMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.FootnoteDescriptionDeleteForm
    success_path = "detail"
