from django.db import models
from psycopg.types.range import DateRange


class GoodsNomenclatureLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    item_id = models.CharField(max_length=10)
    suffix = models.CharField(max_length=2)
    statistical = models.BooleanField()


class GoodsNomenclatureLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(GoodsNomenclatureLatest, models.DO_NOTHING)


class GoodsNomenclatureIndentLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    indent = models.IntegerField()
    indented_goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class GoodsNomenclatureIndentLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        GoodsNomenclatureIndentLatest,
        models.DO_NOTHING,
    )


class GoodsNomenclatureSuccessorLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    absorbed_into_goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
    )
    replaced_goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclaturesuccessor_replaced_goods_nomenclature_set",
    )


class GoodsNomenclatureSuccessorLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        GoodsNomenclatureSuccessorLatest,
        models.DO_NOTHING,
    )


class GoodsNomenclatureOriginLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    derived_from_goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
    )
    new_goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclatureorigin_new_goods_nomenclature_set",
    )


class GoodsNomenclatureOriginLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        GoodsNomenclatureOriginLatest,
        models.DO_NOTHING,
    )


class GoodsNomenclatureDescriptionLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class GoodsNomenclatureDescriptionLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        GoodsNomenclatureDescriptionLatest,
        models.DO_NOTHING,
    )


class FootnoteAssociationGoodsNomenclatureLatest(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    # associated_footnote = models.ForeignKey("FootnotesFootnote", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        GoodsNomenclatureLookUp,
        models.DO_NOTHING,
    )


class FootnoteAssociationGoodsNomenclatureLookUp(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    current_version = models.ForeignKey(
        FootnoteAssociationGoodsNomenclatureLatest,
        models.DO_NOTHING,
    )
