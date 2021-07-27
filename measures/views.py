from typing import Type

from rest_framework import viewsets

from common.models import TrackedModel
from common.serializers import AutoCompleteSerializer
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures import forms
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.models import Measure
from measures.models import MeasureType
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftUpdateView


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [MeasureTypeFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return MeasureType.objects.approved_up_to_transaction(tx).order_by(
            "description",
        )


class MeasureMixin:
    model: Type[TrackedModel] = Measure

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return Measure.objects.with_duty_sentence().approved_up_to_transaction(tx)


class MeasureList(MeasureMixin, TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    queryset = Measure.objects.with_duty_sentence().latest_approved()
    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter


class MeasureDetail(MeasureMixin, TrackedModelDetailView):
    model = Measure
    template_name = "measures/detail.jinja"
    queryset = Measure.objects.with_duty_sentence().latest_approved()


class MeasureUpdate(
    MeasureMixin,
    TrackedModelDetailMixin,
    DraftUpdateView,
):
    form_class = forms.MeasureForm
    permission_required = "common.change_trackedmodel"
    template_name = "measures/edit.jinja"
    queryset = Measure.objects.with_duty_sentence()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        tx = WorkBasket.get_current_transaction(self.request)

        if hasattr(form, "field"):
            for field in form.fields.values():
                if hasattr(field, "queryset"):
                    field.queryset = field.queryset.approved_up_to_transaction(tx)

        return form


class MeasureConfirmUpdate(MeasureMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"
