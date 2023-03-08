from django.urls import include
from django.urls import path
from rest_framework import routers

from common.paths import get_ui_paths
from measures import views
from measures.conditions import measure_edit_condition_dict

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
        "edit-multiple/",
        views.MeasureEditWizard.as_view(
            url_name="measure-ui-edit-multiple",
            done_step_name="complete",
            condition_dict=measure_edit_condition_dict,
        ),
        name="measure-ui-edit-multiple",
    ),
    path(
        "edit-multiple/<step>/",
        views.MeasureEditWizard.as_view(
            url_name="measure-ui-edit-multiple",
            done_step_name="complete",
            condition_dict=measure_edit_condition_dict,
        ),
        name="measure-ui-edit-multiple",
    ),
    path(
        "delete-multiple-measures/",
        views.MeasureMultipleDelete.as_view(),
        name="measure-ui-delete-multiple",
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

ajax_patterns = [
    path(
        "update-measure-selections/",
        views.MeasureSelectionUpdate.as_view(),
        name="update-measure-selections",
    ),
]


urlpatterns = [
    path("measures/", include(ui_patterns)),
    path("ajax/", include(ajax_patterns)),
    path("api/", include(api_router.urls)),
]
