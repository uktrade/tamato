from rest_framework import permissions
from rest_framework import viewsets

from commodities import models
from commodities import serializers
from commodities.filters import GoodsNomenclatureFilterBackend


class GoodsNomenclatureViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows Goods Nomenclature to be viewed."""

    queryset = models.GoodsNomenclature.objects.latest_approved().prefetch_related(
        "descriptions",
    )
    serializer_class = serializers.GoodsNomenclatureSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [GoodsNomenclatureFilterBackend]
