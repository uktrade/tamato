from django.urls import include
from django.urls import path
from rest_framework import routers

from common.paths import get_ui_paths
from measures import views

api_router = routers.DefaultRouter()
api_router.register(r"measure_types", views.MeasureTypeViewSet, basename="measuretype")

detail = "<sid:sid>"
ui_patterns = [
    *get_ui_paths(views, detail),
    path(
        "create/",
        views.MeasureCreateWizard.as_view(
            url_name="measure-ui-create",
            done_step_name="complete",
        ),
        name="measure-ui-create",
    ),
    path(
        "create/<step>/",
        views.MeasureCreateWizard.as_view(
            url_name="measure-ui-create",
            done_step_name="complete",
        ),
        name="measure-ui-create",
    ),
    path(
        f"{detail}/edit-footnotes/",
        views.MeasureFootnotesUpdate.as_view(),
        name="measure-ui-edit-footnotes",
    ),
]


urlpatterns = [
    path("measures/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
