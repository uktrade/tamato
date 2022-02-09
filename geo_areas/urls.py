from django.urls import include
from django.urls import path
from rest_framework import routers

from common.paths import get_ui_paths
from geo_areas import views

api_router = routers.DefaultRouter()
api_router.register(r"geographical_areas", views.GeoAreaViewSet, basename="geo_area")

detail = "<sid:sid>"
description_detail = "<sid:described_geographicalarea__sid>/description/<sid:sid>"
ui_patterns = get_ui_paths(views, detail, description=description_detail)


urlpatterns = [
    path("geographical-areas/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
