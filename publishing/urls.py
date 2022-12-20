from django.urls import include
from django.urls import path
from django.views.generic.base import RedirectView

from publishing import views

app_name = "publishing"

ui_patterns = [
    path(
        "create/",
        views.PackagedWorkbasketCreateView.as_view(),
        name="packaged-workbasket-queue-ui-create",
    ),
    path(
        "<pk>/confirm-create/",
        views.PackagedWorkbasketConfirmCreate.as_view(),
        name="packaged-workbasket-queue-confirm-create",
    ),
    path(
        "",
        RedirectView.as_view(pattern_name="packaged-workbasket-queue-ui-list"),
    ),
    path(
        "packaging-queue/",
        views.PackagedWorkbasketQueueView.as_view(),
        name="packaged-workbasket-queue-ui-list",
    ),
    path(
        "envelope-queue/",
        views.EnvelopeQueueView.as_view(),
        name="envelope-queue-ui-list",
    ),
]


urlpatterns = [
    path("publishing/", include(ui_patterns)),
]
