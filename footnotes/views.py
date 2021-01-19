from django.http import Http404
from django.views.generic import DetailView
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework.reverse import reverse

from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from footnotes import forms
from footnotes import models
from footnotes.filters import FootnoteFilter
from footnotes.filters import FootnoteFilterBackend
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer
from workbaskets.views.generic import DraftUpdateView
from workbaskets.views.mixins import WithCurrentWorkBasket


class FootnoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows footnotes to be viewed and edited.
    """

    queryset = (
        models.Footnote.objects.current()
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


class FootnoteList(TamatoListView):
    queryset = (
        models.Footnote.objects.current()
        .select_related("footnote_type")
        .prefetch_related("descriptions")
    )
    template_name = "footnotes/list.jinja"
    filterset_class = FootnoteFilter
    search_fields = [
        "footnote_id",
        "footnote_type__footnote_type_id",
        "descriptions__description",
        "footnote_type__description",
    ]


class FootnoteDetail(TrackedModelDetailView):
    model = models.Footnote
    template_name = "footnotes/detail.jinja"
    queryset = (
        models.Footnote.objects.current()
        .select_related("footnote_type")
        .prefetch_related("descriptions")
    )


class FootnoteUpdate(TrackedModelDetailMixin, DraftUpdateView):
    form_class = forms.FootnoteForm
    queryset = (
        models.Footnote.objects.current()
        .select_related("footnote_type")
        .prefetch_related("descriptions")
    )
    template_name = "footnotes/edit.jinja"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["footnote_type"].disabled = True
        form.fields["footnote_id"].disabled = True
        return form

    def get_success_url(self):
        return reverse("footnote-ui-confirm-update", kwargs=self.kwargs)


class FootnoteConfirmUpdate(FootnoteDetail):
    template_name = "footnotes/confirm_update.jinja"


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
                f"footnote id, and a period sid in the URLconf."
            )

        queryset = queryset.filter(**self.kwargs)

        try:
            return queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(f"No footnote description matching the query")


class FootnoteDescriptionUpdate(FootnoteDescriptionMixin, DraftUpdateView):
    form_class = forms.FootnoteDescriptionForm
    queryset = models.FootnoteDescription.objects.current()
    template_name = "footnotes/edit_description.jinja"

    def get_success_url(self):
        return self.object.get_url("confirm-update")


class FootnoteDescriptionConfirmUpdate(
    WithCurrentWorkBasket, FootnoteDescriptionMixin, DetailView
):
    queryset = models.FootnoteDescription.objects.current()
    template_name = "footnotes/confirm_update_description.jinja"


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnote types to be viewed or edited.
    """

    queryset = models.FootnoteType.objects.current()
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
