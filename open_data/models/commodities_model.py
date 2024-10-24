from django.db import models
from psycopg.types.range import DateRange


class ReportGoodsNomenclature(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    item_id = models.CharField(max_length=10)
    suffix = models.CharField(max_length=2)
    statistical = models.BooleanField()


class ReportGoodsNomenclatureIndent(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    indent = models.IntegerField()
    indented_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class ReportGoodsNomenclatureSuccessor(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    absorbed_into_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    replaced_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclaturesuccessor_replaced_goods_nomenclature_set",
    )


class ReportGoodsNomenclatureOrigin(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    derived_from_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    new_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclatureorigin_new_goods_nomenclature_set",
    )


class ReportGoodsNomenclatureDescription(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class ReportFootnoteAssociationGoodsNomenclature(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    associated_footnote = models.ForeignKey("ReportFootnote", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
