from rest_framework import serializers

from commodities import models


class CommoditySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Commodity
        fields = ["code"]
