from django.urls import include
from django.urls import path
from rest_framework import routers

from workbaskets.views import api as api_views
from workbaskets.views import ui as ui_views

app_name = "workbaskets"

api_router = routers.DefaultRouter()
api_router.register(r"workbaskets", api_views.WorkBasketViewSet)

ui_patterns = [
    path(
        "",
        ui_views.SelectWorkbasketView.as_view(),
        name="workbasket-ui-list",
    ),
    path(
        "create/",
        ui_views.WorkBasketCreate.as_view(),
        name="workbasket-ui-create",
    ),
    path(
        f"<pk>/edit/",
        ui_views.EditWorkbasketView.as_view(),
        name="edit-workbasket",
    ),
    path(
        "download",
        ui_views.download_envelope,
        name="workbasket-download",
    ),
    path(
        f"<pk>/",
        ui_views.WorkBasketDetail.as_view(),
        name="workbasket-ui-detail",
    ),
    path(
        f"<pk>/confirm-create/",
        ui_views.WorkBasketConfirmCreate.as_view(),
        name="workbasket-ui-confirm-create",
    ),
    path(
        f"<pk>/submit/",
        ui_views.WorkBasketSubmit.as_view(),
        name="workbasket-ui-submit",
    ),
    path(
        f"<pk>/delete-changes/",
        ui_views.WorkBasketDeleteChanges.as_view(),
        name="workbasket-ui-delete-changes",
    ),
    path(
        f"<pk>/delete-changes-done/",
        ui_views.WorkBasketDeleteChangesDone.as_view(),
        name="workbasket-ui-delete-changes-done",
    ),
    path(
        "list-all",
        ui_views.WorkBasketList.as_view(),
        name="workbasket-ui-list-all",
    ),
    path(
        f"<pk>/changes/",
        ui_views.WorkBasketChanges.as_view(),
        name="workbasket-ui-changes",
    ),
]

urlpatterns = [
    path("workbaskets/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
