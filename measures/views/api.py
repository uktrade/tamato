from rest_framework import viewsets

from common.serializers import AutoCompleteSerializer
from measures import models
from measures.filters import MeasureTypeFilterBackend
from workbaskets.models import WorkBasket


class MeasureTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure types to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [MeasureTypeFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.MeasureType.objects.approved_up_to_transaction(tx).order_by(
            "description",
        )
