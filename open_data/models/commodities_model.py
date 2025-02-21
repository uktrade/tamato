from django.db import models

from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureOrigin
from commodities.models import GoodsNomenclatureSuccessor
from commodities.models.code import CommodityCode
from common.fields import TaricDateRangeField
from open_data.models.utils import ReportModel


class ReportGoodsNomenclature(ReportModel):
    shadowed_model = GoodsNomenclature
    extra_where = " AND valid_between @> CURRENT_DATE"

    trackedmodel_ptr = models.ForeignKey(
        shadowed_model,
        models.DO_NOTHING,
        primary_key=True,
        db_column="trackedmodel_ptr_id",
    )
    valid_between = TaricDateRangeField(db_index=True)
    sid = models.IntegerField()
    item_id = models.CharField(max_length=10)
    suffix = models.CharField(max_length=2)
    statistical = models.BooleanField()

    indent = models.IntegerField(null=True)
    description = models.TextField(blank=True, null=True)
    parent_trackedmodel_ptr = models.ForeignKey(
        "self",
        models.DO_NOTHING,
        null=True,
    )

    @property
    def code(self) -> CommodityCode:
        """Returns a CommodityCode instance for the good."""
        return CommodityCode(code=self.item_id)

    class Meta:
        db_table = ReportModel.create_table_name(GoodsNomenclature)


class ReportGoodsNomenclatureSuccessor(ReportModel):
    shadowed_model = GoodsNomenclatureSuccessor
    trackedmodel_ptr = models.ForeignKey(
        shadowed_model,
        models.DO_NOTHING,
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

    trackedmodel_ptr = models.ForeignKey(
        shadowed_model,
        models.DO_NOTHING,
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


class ReportFootnoteAssociationGoodsNomenclature(ReportModel):
    shadowed_model = FootnoteAssociationGoodsNomenclature

    trackedmodel_ptr = models.ForeignKey(
        shadowed_model,
        models.DO_NOTHING,
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
