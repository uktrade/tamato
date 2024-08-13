from rest_framework import serializers

from commodities import models
from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.serializers import ValidityStartSerializerMixin
from footnotes.serializers import FootnoteSerializer


class SimpleGoodsNomenclatureSerializer(
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
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


class SimpleGoodsNomenclatureDescriptionSerializer(
    TrackedModelSerializerMixin,
    ValidityStartSerializerMixin,
):
    class Meta:
        model = models.GoodsNomenclatureDescription
        fields = [
            "sid",
            "description",
            "update_type",
            "record_code",
            "subrecord_code",
            "period_record_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "validity_start",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureSerializer(TrackedModelSerializerMixin,
                                  ValiditySerializerMixin):
    sid = serializers.IntegerField()
    descriptions = SimpleGoodsNomenclatureDescriptionSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = models.GoodsNomenclature
        fields = [
            "id",
            "sid",
            "item_id",
            "suffix",
            "statistical",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "descriptions",
            "start_date",
            "end_date",
            "valid_between",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureIndentSerializer(
    TrackedModelSerializerMixin,
    ValidityStartSerializerMixin,
):
    indented_goods_nomenclature = SimpleGoodsNomenclatureSerializer(
        read_only=True)
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
            "validity_start",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureDescriptionSerializer(
    TrackedModelSerializerMixin,
    ValidityStartSerializerMixin,
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
            "validity_start",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GoodsNomenclatureOriginSerializer(TrackedModelSerializerMixin):
    new_goods_nomenclature = SimpleGoodsNomenclatureSerializer(read_only=True)
    derived_from_goods_nomenclature = SimpleGoodsNomenclatureSerializer(
        read_only=True)

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
    replaced_goods_nomenclature = SimpleGoodsNomenclatureSerializer(
        read_only=True)
    absorbed_into_goods_nomenclature = SimpleGoodsNomenclatureSerializer(
        read_only=True)

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
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
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


class ZGoodsNomenclatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GoodsNomenclature
        fields = [
            "sid",
            "item_id",
            "suffix",
            "valid_between",
        ]


class ZGoodsNomenclatureIndentSerializer(serializers.ModelSerializer):
    indented_goods_nomenclature_sid = serializers.CharField(
        source="indented_goods_nomenclature.sid", read_only=True)
    indented_goods_nomenclature_item_id = serializers.CharField(
        source="indented_goods_nomenclature.item_id", read_only=True)
    indent_sid = serializers.CharField(source="sid", read_only=True)
    class Meta:
        model = models.GoodsNomenclatureIndent
        fields = [
            "indented_goods_nomenclature_sid",
            "indented_goods_nomenclature_item_id",
            "indent_sid",
            "indent",
            "update_type",
            "validity_start",
        ]


class ZGoodsNomenclatureDescriptionSerializer(serializers.ModelSerializer):
    goods_nomenclature_sid = serializers.CharField(
        source="described_goods_nomenclature.sid", read_only=True)
    goods_nomenclature_item_id = serializers.CharField(
        source="described_goods_nomenclature.item_id", read_only=True)
    description_sid = serializers.CharField(
        source="sid", read_only=True)

    class Meta:
        model = models.GoodsNomenclatureDescription
        fields = [
            "goods_nomenclature_sid",
            "goods_nomenclature_item_id",
            "description_sid",
            "description",
            "validity_start",
        ]


class ZGoodsNomenclatureOriginSerializer(serializers.ModelSerializer):
    derived_from_goods_nomenclature_item_id = serializers.CharField(
        source="derived_from_goods_nomenclature.item_id", read_only=True)
    derived_from_goods_nomenclature_sid = serializers.CharField(
        source="derived_from_goods_nomenclature.sid", read_only=True)
    new_goods_nomenclature_item_id = serializers.CharField(
        source="new_goods_nomenclature.item_id", read_only=True)
    new_goods_nomenclature_sid = serializers.CharField(
        source="new_goods_nomenclature.sid", read_only=True)

    class Meta:
        model = models.GoodsNomenclatureOrigin
        fields = [
            "derived_from_goods_nomenclature_sid",
            "derived_from_goods_nomenclature_item_id",
            "new_goods_nomenclature_item_id",
            "new_goods_nomenclature_sid",
        ]

class ZGoodsNomenclatureSuccessorSerializer(serializers.ModelSerializer):
    replaced_goods_nomenclature_item_id = serializers.CharField(
        source="replaced_goods_nomenclature.item_id", read_only=True)
    replaced_goods_nomenclature_sid = serializers.CharField(
        source="replaced_goods_nomenclature.sid", read_only=True)
    absorbed_into_goods_nomenclature_item_id = serializers.CharField(
        source="absorbed_into_goods_nomenclature.item_id", read_only=True)
    absorbed_into_goods_nomenclature_sid = serializers.CharField(
        source="absorbed_into_goods_nomenclature.sid", read_only=True)

    class Meta:
        model = models.GoodsNomenclatureOrigin
        fields = [
            "replaced_goods_nomenclature_item_id",
            "replaced_goods_nomenclature_sid",
            "absorbed_into_goods_nomenclature_item_id",
            "absorbed_into_goods_nomenclature_sid",
        ]


class GoodsNomenclaturePlusSerializer(TrackedModelSerializerMixin):
    goods_nomenclature = ZGoodsNomenclatureSerializer(source='*')
    goods_nomenclature_indent = serializers.SerializerMethodField()
    goods_nomenclature_description = serializers.SerializerMethodField()
    goods_nomenclature_origin = serializers.SerializerMethodField()
    goods_nomenclature_successor = serializers.SerializerMethodField()


    class Meta:
        model = models.GoodsNomenclature
        fields = [
            "goods_nomenclature",
            "goods_nomenclature_indent",
            "goods_nomenclature_description",
            "goods_nomenclature_origin",
            "goods_nomenclature_successor",
        ]

    def get_goods_nomenclature_indent(self, obj):
        indent = models.GoodsNomenclatureIndent.objects.filter(
            indented_goods_nomenclature_id=obj.id).latest_approved().first()
        if indent:
            return ZGoodsNomenclatureIndentSerializer(indent).data
        return None

    def get_goods_nomenclature_description(self, obj):
        description = models.GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature_id=obj.id).latest_approved().first()
        if description:
            return ZGoodsNomenclatureDescriptionSerializer(description).data
        return None

    def get_goods_nomenclature_origin(self, obj):
        origin = models.GoodsNomenclatureOrigin.objects.filter(
            new_goods_nomenclature_id=obj.id).latest_approved().first()
        if origin:
            return ZGoodsNomenclatureOriginSerializer(origin).data
        return None

    def get_goods_nomenclature_successor(self, obj):
        successor = models.GoodsNomenclatureSuccessor.objects.filter(
            replaced_goods_nomenclature=obj.id).latest_approved().first()
        if successor:
            return ZGoodsNomenclatureSuccessorSerializer(successor).data
        return None
