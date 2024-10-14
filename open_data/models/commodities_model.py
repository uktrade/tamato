from django.db import models
from psycopg.types.range import DateRange


class CommoditiesGoodsnomenclature(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    sid = models.IntegerField()
    item_id = models.CharField(max_length=10)
    suffix = models.CharField(max_length=2)
    statistical = models.BooleanField()


class CommoditiesGoodsnomenclatureindent(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    indent = models.IntegerField()
    indented_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class CommoditiesGoodsnomenclaturesuccessor(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    absorbed_into_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    replaced_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclaturesuccessor_replaced_goods_nomenclature_set",
    )


class CommoditiesGoodsnomenclatureorigin(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    derived_from_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    new_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclatureorigin_new_goods_nomenclature_set",
    )


class CommoditiesGoodsnomenclaturedescription(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()


class CommoditiesFootnoteassociationgoodsnomenclature(models.Model):
    trackedmodel_ptr = models.IntegerField(primary_key=True)
    valid_between = DateRange()
    associated_footnote = models.ForeignKey("FootnotesFootnote", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
