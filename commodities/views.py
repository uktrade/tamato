from rest_framework import permissions
from rest_framework import viewsets

from commodities.filters import GoodsNomenclatureFilterBackend
from commodities.models import GoodsNomenclature
from common.serializers import AutoCompleteSerializer
from workbaskets.models import WorkBasket


class GoodsNomenclatureViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows Goods Nomenclature to be viewed."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [GoodsNomenclatureFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return GoodsNomenclature.objects.approved_up_to_transaction(
            tx,
        ).prefetch_related("descriptions")
