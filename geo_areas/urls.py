from django.urls import include
from django.urls import path
from rest_framework import routers

from geo_areas import views

api_router = routers.DefaultRouter()
api_router.register(r"geographical_areas", views.GeoAreaViewSet, basename="geoarea")

ui_patterns = [
    path(
        "",
        views.GeographicalAreaList.as_view(),
        name="geoarea-ui-list",
    ),
    path(
        "<sid:sid>/",
        views.GeographicalAreaDetail.as_view(),
        name="geoarea-ui-detail",
    ),
    path(
        "<sid:sid>/create-description/",
        views.GeographicalAreaCreateDescription.as_view(),
        name="geoarea-ui-create-description",
    ),
    path(
        "<sid:described_geographicalarea__sid>/description/<sid:sid>/confirm-update/",
        views.GeographicalAreaDescriptionConfirmUpdate.as_view(),
        name="geographical_area_description-ui-confirm-update",
    ),
]


urlpatterns = [
    path("geographical-areas/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
