from datetime import datetime
from datetime import timezone

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import generic
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.reverse import reverse

from common.validators import UpdateType
from footnotes import forms
from footnotes import models
from footnotes.filters import FootnoteFilterBackend
from footnotes.serializers import FootnoteSerializer
from footnotes.serializers import FootnoteTypeSerializer
from workbaskets.views import get_current_workbasket
from workbaskets.views import require_current_workbasket


class FootnoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows footnotes to be viewed and edited.
    """

    queryset = models.Footnote.objects.all().prefetch_related("descriptions")
    serializer_class = FootnoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [FootnoteFilterBackend]
    search_fields = [
        "footnote_id",
        "footnote_type__footnote_type_id",
        "descriptions__description",
        "footnote_type__description",
    ]


class CurrentWorkBasketMixin:
    def get_queryset(self):
        workbasket = get_current_workbasket(self.request)
        if self.queryset is None:
            if self.model:
                qs = self.model.objects.current()
                if workbasket:
                    qs |= self.model.objects.filter(workbasket=workbasket)
                return qs
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a QuerySet. Define "
                    "%(cls)s.model, %(cls)s.queryset, or override "
                    "%(cls)s.get_queryset()." % {"cls": self.__class__.__name__}
                )
        if workbasket:
            return self.queryset | self.queryset.model.objects.filter(
                workbasket=workbasket
            )
        return self.queryset


class FootnoteList(CurrentWorkBasketMixin, generic.ListView):
    model = models.Footnote
    template_name = "footnotes/list.jinja"


class FootnoteMixin:
    required_url_kwargs = ["footnote_type__footnote_type_id", "footnote_id"]

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        if not all(key in self.kwargs for key in self.required_url_kwargs):
            raise AttributeError(
                f"{self.__class__.__name__} must be called with a footnote type id and "
                f"footnote id in the URLconf."
            )

        queryset = queryset.filter(**self.kwargs)

        try:
            return queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(f"No footnote matching the query {self.kwargs}")


class FootnoteDetail(CurrentWorkBasketMixin, FootnoteMixin, generic.DetailView):
    model = models.Footnote
    template_name = "footnotes/detail.jinja"


@method_decorator(require_current_workbasket, name="dispatch")
class FootnoteUpdate(CurrentWorkBasketMixin, FootnoteMixin, generic.UpdateView):
    form_class = forms.FootnoteForm
    queryset = models.Footnote.objects.current()
    template_name = "footnotes/edit.jinja"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["footnote_type"].disabled = True
        form.fields["footnote_id"].disabled = True
        return form

    def get_success_url(self):
        return reverse("footnote-ui-confirm-update", kwargs=self.kwargs)

    def form_valid(self, form):
        self.object = self.object.new_draft(
            workbasket=get_current_workbasket(self.request),
            update_type=UpdateType.UPDATE,
            valid_between=form.cleaned_data.get("valid_between"),
        )
        return super().form_valid(form)


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


@method_decorator(require_current_workbasket, name="dispatch")
class FootnoteDescriptionUpdate(
    CurrentWorkBasketMixin, FootnoteDescriptionMixin, generic.UpdateView
):
    form_class = forms.FootnoteDescriptionForm
    queryset = models.FootnoteDescription.objects.current()
    template_name = "footnotes/edit_description.jinja"

    def get_success_url(self):
        return self.object.get_url("confirm-update")

    def form_valid(self, form):
        valid_between = form.cleaned_data.get("valid_between")
        description = form.cleaned_data.get("description")

        self.object = self.object.new_draft(
            workbasket=get_current_workbasket(self.request),
            update_type=UpdateType.UPDATE,
            valid_between=valid_between,
            description=description,
        )
        return super().form_valid(form)


class FootnoteDescriptionConfirmUpdate(
    CurrentWorkBasketMixin, FootnoteDescriptionMixin, generic.DetailView
):
    queryset = models.FootnoteDescription.objects.current()
    template_name = "footnotes/confirm_update_description.jinja"


class FootnoteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows footnote types to be viewed or edited.
    """

    queryset = models.FootnoteType.objects.all().prefetch_related(
        "footnotetypedescription_set"
    )
    serializer_class = FootnoteTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
