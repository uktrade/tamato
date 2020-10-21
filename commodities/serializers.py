from rest_framework import serializers

from commodities import models
from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from footnotes.serializers import FootnoteSerializer


class SimpleGoodsNomenclatureSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    class Meta:
        model = models.GoodsNomenclature
        fields = [
            "sid",
            "item_id",
            "suffix",
            "record_code",
            "subrecord_code",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    origin = SimpleGoodsNomenclatureSerializer(read_only=True)
    succeeding_goods = SimpleGoodsNomenclatureSerializer(read_only=True, many=True)

    class Meta:
        model = models.GoodsNomenclature
        fields = [
            "sid",
            "item_id",
            "suffix",
            "statistical",
            "origin",
            "succeeding_goods",
            "update_type",
            "record_code",
            "subrecord_code",
            "origin_record_code",
            "origin_subrecord_code",
            "successor_record_code",
            "successor_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureIndentSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    indent = serializers.SerializerMethodField()
    indented_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)

    def get_indent(self, obj: models.GoodsNomenclatureIndent):
        depth = obj.nodes.first().depth
        indent = 0 if depth < 3 else depth - 2
        return str(indent).zfill(2)

    class Meta:
        model = models.GoodsNomenclatureIndent
        fields = [
            "sid",
            "indent",
            "indented_goods_nomenclature",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureDescriptionSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    described_goods_nomenclature = GoodsNomenclatureSerializer(read_only=True)

    class Meta:
        model = models.GoodsNomenclatureDescription
        fields = [
            "sid",
            "described_goods_nomenclature",
            "description",
            "update_type",
            "record_code",
            "subrecord_code",
            "period_record_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class FootnoteAssociationGoodsNomenclatureSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)
    associated_footnote = FootnoteSerializer(read_only=True)

    class Meta:
        model = models.FootnoteAssociationGoodsNomenclature
        fields = [
            "goods_nomenclature",
            "associated_footnote",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]
