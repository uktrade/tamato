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
        "search/",
        views.MeasureSearch.as_view(),
        name="measure-ui-search",
    ),
    path(
        "create/",
        views.MeasureCreateWizard.as_view(
            url_name="measure-ui-create",
            done_step_name="complete",
        ),
        name="measure-ui-create",
    ),
    path(
        "<sid:sid>/copy/",
        views.MeasureCopy.as_view(),
        name="measure-ui-copy",
    ),
    path(
        "<sid:sid>/confirm-copy/",
        views.MeasureConfirmCopy.as_view(),
        name="measure-ui-confirm-copy",
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
        "edit/done-async/<int:expected_measures_count>/",
        views.MeasuresWizardAsyncConfirm.as_view(),
        name="measure-ui-edit-async-confirm",
    ),
    path(
        "edit/done-sync/<int:edited_or_created_measures_count>/",
        views.MeasuresWizardSyncConfirm.as_view(),
        name="measure-ui-edit-sync-confirm",
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
        "create/done-async/<int:expected_measures_count>/",
        views.MeasuresWizardAsyncConfirm.as_view(),
        name="measure-ui-create-async-confirm",
    ),
    path(
        "create/done-sync/<int:edited_or_created_measures_count>/",
        views.MeasuresWizardSyncConfirm.as_view(),
        name="measure-ui-create-sync-confirm",
    ),
    path(
        f"{detail}/edit-footnotes/",
        views.MeasureFootnotesUpdate.as_view(),
        name="measure-ui-edit-footnotes",
    ),
    path(
        "create-process-queue/",
        views.MeasuresCreateProcessQueue.as_view(),
        name="measure-create-process-queue",
    ),
    path(
        "edit-process-queue/",
        views.MeasuresEditProcessQueue.as_view(),
        name="measure-edit-process-queue",
    ),
    path(
        "cancel-bulk-processor-task/<int:pk>/",
        views.CancelBulkProcessorTask.as_view(),
        name="cancel-bulk-processor-task",
    ),
    path(
        "cancel-bulk-processor-task/<int:pk>/done/",
        views.CancelBulkProcessorTaskDone.as_view(),
        name="cancel-bulk-processor-task-done",
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
