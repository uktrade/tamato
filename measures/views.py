from common.views import TamatoListView
from measures import models
from measures.filters import MeasureFilter


class MeasureList(TamatoListView):
    """UI endpoint for viewing and filtering Measures."""

    queryset = models.Measure.objects.with_duty_sentence()
    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter
