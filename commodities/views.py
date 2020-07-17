from rest_framework import permissions
from rest_framework import viewsets

from commodities import models
from commodities import serializers


class GoodsNomenclatureViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Goods Nomenclature to be viewed.
    """

    queryset = models.GoodsNomenclature.objects.all()
    serializer_class = serializers.GoodsNomenclatureSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "item_id"]
