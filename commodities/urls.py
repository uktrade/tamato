from django.urls import include
from django.urls import path
from rest_framework import routers

from commodities import views

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
]
