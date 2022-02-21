from django.urls import include
from django.urls import path
from rest_framework import routers

from workbaskets import views

app_name = "workbaskets"

api_router = routers.DefaultRouter()
api_router.register(r"workbaskets", views.WorkBasketViewSet)

ui_patterns = [
    path(
        "",
        views.WorkBasketList.as_view(),
        name="workbasket-ui-list",
    ),
    path(
        f"<pk>/",
        views.WorkBasketDetail.as_view(),
        name="workbasket-ui-detail",
    ),
    path(
        f"<pk>/submit/",
        views.WorkBasketSubmit.as_view(),
        name="workbasket-ui-submit",
    ),
    path(
        f"<pk>/delete-changes/",
        views.WorkBasketDeleteChanges.as_view(),
        name="workbasket-ui-delete-changes",
    ),
    path(
        f"<pk>/delete-changes-done/",
        views.WorkBasketDeleteChangesDone.as_view(),
        name="workbasket-ui-delete-changes-done",
    ),
    path(
        "download",
        views.download_envelope,
        name="workbasket-download",
    ),
]

urlpatterns = [
    path("workbaskets/", include(ui_patterns)),
    path("api/", include(api_router.urls)),
]
