from rest_framework import viewsets

from common.views import TamatoListView
from common.views import TrackedModelDetailView
from measures import models
from measures.filters import MeasureFilter
from measures.filters import MeasureTypeFilterBackend
from measures.serializers import MeasureTypeSerializer


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    queryset = models.MeasureType.objects.latest_approved()
    serializer_class = MeasureTypeSerializer
    filter_backends = [MeasureTypeFilterBackend]


class MeasureList(TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    queryset = models.Measure.objects.with_duty_sentence().latest_approved()
    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter


class MeasureDetail(TrackedModelDetailView):
    model = models.Measure
    template_name = "measures/detail.jinja"
    queryset = models.Measure.objects.with_duty_sentence().latest_approved()
