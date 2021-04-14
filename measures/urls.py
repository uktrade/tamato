from django.urls import include
from django.urls import path
from rest_framework import routers

from measures import views

api_router = routers.DefaultRouter()
api_router.register(r"measure_types", views.MeasureTypeViewSet)

ui_patterns = [
    path(
        "",
        views.MeasureList.as_view(),
        name="measure-ui-list",
    ),
    path(
        "<sid:sid>/",
        views.MeasureDetail.as_view(),
        name="measure-ui-detail",
    ),
    path(
        "<sid:sid>/edit/",
        views.MeasureUpdate.as_view(),
        name="measure-ui-edit",
    ),
    path(
        "<sid:sid>/confirm-update/",
        views.MeasureConfirmUpdate.as_view(),
        name="measure-ui-confirm-update",
    ),
]


urlpatterns = [
    path("measures/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
