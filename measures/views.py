from rest_framework import viewsets

from common.models import TrackedModel
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.forms import MeasureForm
from measures.models import Measure
from measures.models import MeasureType
from measures.serializers import MeasureTypeSerializer
from workbaskets.models import WorkBasket
from workbaskets.views.generic import DraftUpdateView


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    queryset = MeasureType.objects.latest_approved()
    serializer_class = MeasureTypeSerializer
    filter_backends = [MeasureTypeFilterBackend]


class MeasureMixin:
    model: type[TrackedModel] = Measure

    def get_queryset(self):
        workbasket = WorkBasket.current(self.request)
        tx = None
        if workbasket:
            tx = workbasket.transactions.order_by("order").last()

        return Measure.objects.with_duty_sentence().approved_up_to_transaction(tx)


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    queryset = MeasureType.objects.latest_approved()
    serializer_class = MeasureTypeSerializer
    filter_backends = [MeasureTypeFilterBackend]


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
    form_class = MeasureForm
    permission_required = "common.change_trackedmodel"
    template_name = "measures/edit.jinja"
    queryset = Measure.objects.with_duty_sentence()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class MeasureConfirmUpdate(MeasureMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"
