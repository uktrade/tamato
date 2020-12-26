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
    sid = serializers.IntegerField()

    class Meta:
        model = models.GoodsNomenclature
        fields = [
            "sid",
            "item_id",
            "suffix",
            "statistical",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureIndentSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    indented_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)
    sid = serializers.IntegerField()

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
    sid = serializers.IntegerField()

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
class GoodsNomenclatureOriginSerializer(TrackedModelSerializerMixin):
    new_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)
    derived_from_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)

    class Meta:
        model = models.GoodsNomenclatureOrigin
        fields = [
            "new_goods_nomenclature",
            "derived_from_goods_nomenclature",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureSuccessorSerializer(TrackedModelSerializerMixin):
    replaced_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)
    absorbed_into_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)

    class Meta:
        model = models.GoodsNomenclatureSuccessor
        fields = [
            "replaced_goods_nomenclature",
            "absorbed_into_goods_nomenclature",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
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
