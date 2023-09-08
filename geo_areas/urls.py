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

ui_patterns += [
    path(
        "",
        views.GeoAreaSearch.as_view(),
        name="geo_areas-ui-search",
    ),
    path(
        "<sid:sid>/membership-create/",
        views.GeographicalMembershipsCreate.as_view(),
        name="geo_area-ui-membership-create",
    ),
    path(
        "<sid:sid>/membership/confirm-create/",
        views.GeographicalMembershipConfirmCreate.as_view(),
        name="geo_area-ui-membership-confirm-create",
    ),
]


urlpatterns = [
    path("geographical-areas/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
