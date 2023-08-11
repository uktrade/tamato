from django.urls import include
from django.urls import path
from django.urls import register_converter
from rest_framework import routers

from commodities import views
from common.path_converters import TaricDateRangeConverter
from footnotes.path_converters import FootnoteIdConverter
from footnotes.path_converters import FootnoteTypeIdConverter

register_converter(FootnoteIdConverter, "footnote_id")
register_converter(FootnoteTypeIdConverter, "footnote_type_id")
register_converter(TaricDateRangeConverter, "taric_date_range")

footnote_association_pattern = (
    "commodities/<sid:goods_nomenclature__sid>"
    "/footnote-associations/"
    "<footnote_type_id:associated_footnote__footnote_type__footnote_type_id>"
    "<footnote_id:associated_footnote__footnote_id>"
    "/date/<taric_date_range:valid_between>"
)

api_router = routers.DefaultRouter()
api_router.register(
    r"goods_nomenclature",
    views.GoodsNomenclatureViewset,
    basename="goodsnomenclature",
)

urlpatterns = [
    path("api/", include(api_router.urls)),
    path(
        "commodities/",
        views.CommodityList.as_view(),
        name="commodity-ui-list",
    ),
    path(
        f"commodities/<sid>/",
        views.CommodityDetail.as_view(),
        name="commodity-ui-detail",
    ),
    path(
        f"commodities/<sid>/footnotes/",
        views.CommodityDetailFootnotes.as_view(),
        name="commodity-ui-detail-footnotes",
    ),
    path(
        f"commodities/<sid>/hierarchy/",
        views.CommodityHierarchy.as_view(),
        name="commodity-ui-detail-hierarchy",
    ),
    path(
        f"commodities/<sid>/measures-on-declarable-commodities/",
        views.MeasuresOnDeclarableCommoditiesList.as_view(),
        name="commodity-ui-detail-measures-declarable",
    ),
    path(
        f"commodities/<sid>/measures-as-defined/",
        views.CommodityMeasuresAsDefinedList.as_view(),
        name="commodity-ui-detail-measures-as-defined",
    ),
    path(
        f"commodities/<sid>/version/",
        views.CommodityVersion.as_view(),
        name="commodity-ui-detail-version",
    ),
    path(
        f"commodities/<sid>/add-footnote/",
        views.CommodityAddFootnote.as_view(),
        name="commodity-ui-add-footnote",
    ),
    path(
        f"commodity-footnotes/<pk>/confirm-create/",
        views.CommodityAddFootnoteConfirm.as_view(),
        name="commodity-ui-add-footnote-confirm",
    ),
    path(
        f"{footnote_association_pattern}/edit/",
        views.FootnoteAssociationGoodsNomenclatureUpdate.as_view(),
        name="footnote_association_goods_nomenclature-ui-edit",
    ),
    path(
        f"{footnote_association_pattern}/edit-update/",
        views.FootnoteAssociationGoodsNomenclatureUpdate.as_view(),
        name="footnote_association_goods_nomenclature-ui-edit-update",
    ),
    path(
        f"{footnote_association_pattern}/edit-create/",
        views.FootnoteAssociationGoodsNomenclatureUpdate.as_view(),
        name="footnote_association_goods_nomenclature-ui-edit-create",
    ),
    path(
        f"{footnote_association_pattern}/confirm-update/",
        views.FootnoteAssociationGoodsNomenclatureConfirmUpdate.as_view(),
        name="footnote_association_goods_nomenclature-ui-confirm-update",
    ),
]
