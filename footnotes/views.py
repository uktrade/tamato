from datetime import datetime
from datetime import timezone

from django.core.exceptions import ImproperlyConfigured
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

from common.models import UpdateType
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
                if workbasket:
                    return self.model._default_manager.current()
                return self.model._default_manager.active()
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a QuerySet. Define "
                    "%(cls)s.model, %(cls)s.queryset, or override "
                    "%(cls)s.get_queryset()." % {"cls": self.__class__.__name__}
                )
        if workbasket:
            return self.queryset.current()
        return self.queryset.active()


class FootnoteList(CurrentWorkBasketMixin, generic.ListView):
    model = models.Footnote
    template_name = "footnotes/list.jinja"


class FootnoteMixin:
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        type_id = self.kwargs.get("footnote_type_id")
        id = self.kwargs.get("footnote_id")

        if id is not None:
            queryset = queryset.filter(footnote_id=id)

        if type_id is not None:
            queryset = queryset.filter(footnote_type__footnote_type_id=type_id)

        if id is None and type_id is None:
            raise AttributeError(
                "{self.__class__.__name__} must be called with a footnote type id and "
                "footnote id in the URLconf."
            )

        try:
            return queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(f"No footnote matching the query")


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
            update_type=UpdateType.Update,
            valid_between=form.cleaned_data.get("valid_between"),
        )
        return super().form_valid(form)


class FootnoteConfirmUpdate(FootnoteDetail):
    template_name = "footnotes/confirm_update.jinja"


class FootnoteDescriptionMixin:
    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        type_id = self.kwargs.get("footnote_type_id")
        id = self.kwargs.get("footnote_id")
        period_sid = self.kwargs.get("period_sid")

        if id is not None:
            queryset = queryset.filter(described_footnote__footnote_id=id)

        if type_id is not None:
            queryset = queryset.filter(
                described_footnote__footnote_type__footnote_type_id=type_id
            )

        if period_sid is not None:
            queryset = queryset.filter(description_period_sid=period_sid)

        if id is None and type_id is None and period_sid is None:
            raise AttributeError(
                "{self.__class__.__name__} must be called with a footnote type id, a "
                "footnote id, and a period sid in the URLconf."
            )

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
            update_type=UpdateType.Update,
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
