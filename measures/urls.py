from ajax_select import urls as ajax_select_urls
from django.urls import include
from django.urls import path
from django.urls import re_path
from rest_framework import routers

from measures import views

api_router = routers.DefaultRouter()
api_router.register(r"measure_types", views.MeasureTypeViewSet, basename="measuretype")

ui_patterns = [
    path(
        "",
        views.MeasureList.as_view(),
        name="measure-ui-list",
    ),
    path(
        "create/<sid:sid>/confirm/",
        views.MeasureConfirmCreate.as_view(),
        name="measure-ui-confirm-create",
    ),
    path(
        "create/",
        views.MeasureCreateWizard.as_view(),
        name="measure-ui-create",
    ),
    path(
        "create/<step>/",
        views.MeasureCreateWizard.as_view(),
        name="measure-ui-create",
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
    re_path(r"^ajax_select/", include(ajax_select_urls)),
    path("measures/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
