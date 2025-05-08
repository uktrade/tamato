from rest_framework import viewsets

from common.serializers import AutoCompleteSerializer
from measures import models
from measures.filters import MeasureActionFilterBackend
from measures.filters import MeasureConditionCodeFilterBackend
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


class MeasureConditionCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure condition codes to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [MeasureConditionCodeFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.MeasureConditionCode.objects.approved_up_to_transaction(
            tx,
        ).order_by(
            "code",
        )


class MeasureActionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows measure actions to be viewed."""

    serializer_class = AutoCompleteSerializer
    filter_backends = [MeasureActionFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.MeasureAction.objects.approved_up_to_transaction(tx).order_by(
            "code",
        )
