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
        "<sid:sid>/membership-create/",
        views.GeographicalMembershipsCreate.as_view(),
        name="geo_area-ui-membership-create",
    ),
    path(
        "<sid:sid>/membership/confirm-create/",
        views.GeographicalMembershipConfirmCreate.as_view(),
        name="geo_area-ui-membership-confirm-create",
    ),
    path(
        f"{detail}/descriptions/",
        views.GeoAreaDetailDescriptions.as_view(),
        name="geo_area-ui-detail-descriptions",
    ),
    path(
        f"{detail}/version-control/",
        views.GeoAreaDetailVersionControl.as_view(),
        name="geo_area-ui-detail-version-control",
    ),
    path(
        f"{detail}/memberships/",
        views.GeoAreaDetailMemberships.as_view(),
        name="geo_area-ui-detail-memberships",
    ),
    path(
        f"{detail}/measures/",
        views.GeoAreaDetailMeasures.as_view(),
        name="geo_area-ui-detail-measures",
    ),
]


urlpatterns = [
    path("geographical-areas/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
