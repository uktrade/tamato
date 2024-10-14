# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class CommoditiesGoodsnomenclature(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    sid = models.IntegerField()
    item_id = models.CharField(max_length=10)
    suffix = models.CharField(max_length=2)
    statistical = models.BooleanField()

    class Meta:
        managed = False
        db_table = "commodities_goodsnomenclature"


class CommoditiesGoodsnomenclatureindent(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    sid = models.IntegerField()
    indent = models.IntegerField()
    indented_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()

    class Meta:
        managed = False
        db_table = "commodities_goodsnomenclatureindent"


class CommoditiesGoodsnomenclaturesuccessor(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    absorbed_into_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    replaced_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclaturesuccessor_replaced_goods_nomenclature_set",
    )

    class Meta:
        managed = False
        db_table = "commodities_goodsnomenclaturesuccessor"


class CommoditiesGoodsnomenclatureorigin(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    derived_from_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    new_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclatureorigin_new_goods_nomenclature_set",
    )

    class Meta:
        managed = False
        db_table = "commodities_goodsnomenclatureorigin"


class CommoditiesGoodsnomenclaturedescription(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()

    class Meta:
        managed = False
        db_table = "commodities_goodsnomenclaturedescription"


class CommoditiesFootnoteassociationgoodsnomenclature(models.Model):
    trackedmodel_ptr = models.OneToOneField(
        "CommonTrackedmodel",
        models.DO_NOTHING,
        primary_key=True,
    )
    valid_between = models.TextField()  # This field type is a guess.
    associated_footnote = models.ForeignKey("FootnotesFootnote", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        CommoditiesGoodsnomenclature,
        models.DO_NOTHING,
    )

    class Meta:
        managed = False
        db_table = "commodities_footnoteassociationgoodsnomenclature"
