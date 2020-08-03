from commodities.models import GoodsNomenclature
from commodities.serializers import GoodsNomenclatureSerializer
from common.serializers import ValiditySerializerMixin, TrackedModelSerializer
from measures import models


@TrackedModelSerializer.register_polymorphic_model
class MeasureSerializer(ValiditySerializerMixin):
    commodity_code = GoodsNomenclatureSerializer()

    class Meta:
        model = models.Measure
        fields = ["commodity_code", "valid_between"]

    def create(self, validated_data):
        commodity_code = GoodsNomenclature.objects.get(
            **validated_data.pop("commodity_code", {})
        )
        models.Measure.objects.create(commodity_code=commodity_code, **validated_data)
