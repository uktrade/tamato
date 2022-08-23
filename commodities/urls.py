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
        "commodities/import/",
        views.CommodityImportView.as_view(),
        name="commodity-ui-import",
    ),
    path(
        "commodities/import/success/",
        views.CommodityImportSuccessView.as_view(),
        name="commodities-import-success",
    ),
]
