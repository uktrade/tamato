from django.db import models

from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureOrigin
from commodities.models import GoodsNomenclatureSuccessor
from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel


class ReportGoodsNomenclature(ReportModel):
    shadowed_model = GoodsNomenclature

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    item_id = models.CharField(max_length=10)
    suffix = models.CharField(max_length=2)
    statistical = models.BooleanField()

    class Meta:
        db_table = ReportModel.create_table_name(GoodsNomenclature)


class ReportGoodsNomenclatureIndent(ReportModel):
    shadowed_model = GoodsNomenclatureIndent

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    sid = models.IntegerField()
    indent = models.IntegerField()
    indented_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()

    class Meta:
        db_table = ReportModel.create_table_name(GoodsNomenclatureIndent)


class ReportGoodsNomenclatureSuccessor(ReportModel):
    shadowed_model = GoodsNomenclatureSuccessor
    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    absorbed_into_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    replaced_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclaturesuccessor_replaced_goods_nomenclature_set",
    )

    class Meta:
        db_table = ReportModel.create_table_name(GoodsNomenclatureSuccessor)


class ReportGoodsNomenclatureOrigin(ReportModel):
    shadowed_model = GoodsNomenclatureOrigin

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    derived_from_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    new_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
        related_name="commoditiesgoodsnomenclatureorigin_new_goods_nomenclature_set",
    )

    class Meta:
        db_table = ReportModel.create_table_name(GoodsNomenclatureOrigin)


class ReportGoodsNomenclatureDescription(ReportModel):
    shadowed_model = GoodsNomenclatureDescription

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    sid = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    described_goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )
    validity_start = models.DateField()

    class Meta:
        db_table = ReportModel.create_table_name(GoodsNomenclatureDescription)


class ReportFootnoteAssociationGoodsNomenclature(ReportModel):
    shadowed_model = FootnoteAssociationGoodsNomenclature

    trackedmodel_ptr = models.IntegerField(
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    associated_footnote = models.ForeignKey("ReportFootnote", models.DO_NOTHING)
    goods_nomenclature = models.ForeignKey(
        ReportGoodsNomenclature,
        models.DO_NOTHING,
    )

    class Meta:
        db_table = ReportModel.create_table_name(FootnoteAssociationGoodsNomenclature)
