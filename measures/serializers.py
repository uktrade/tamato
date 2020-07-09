from commodities.models import Commodity
from commodities.serializers import CommoditySerializer
from common.serializers import ValiditySerializerMixin
from measures import models


@TrackedModelSerializer.register_polymorphic_model
class MeasureSerializer(ValiditySerializerMixin):
    commodity_code = CommoditySerializer()

    class Meta:
        model = models.Measure
        fields = ["commodity_code", "valid_between"]

    def create(self, validated_data):
        commodity_code = Commodity.objects.get(
            **validated_data.pop("commodity_code", {})
        )
        models.Measure.objects.create(commodity_code=commodity_code, **validated_data)
