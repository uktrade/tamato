from django.urls import include
from django.urls import path
from django.urls import re_path
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
    re_path(
        r"^(?P<sid>\d*)$",
        views.GeographicalAreaDetail.as_view(),
        name="geoarea-ui-detail",
    ),
]


urlpatterns = [
    path("geographical-areas/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
