from django.urls import path
from django.views.generic.base import RedirectView

from publishing import views

app_name = "publishing"

url_prefix = "publishing/"

urlpatterns = [
    path(
        url_prefix + "create/",
        views.PackagedWorkbasketCreateView.as_view(),
        name="packaged-workbasket-queue-ui-create",
    ),
    path(
        url_prefix + "<pk>/confirm-create/",
        views.PackagedWorkbasketConfirmCreate.as_view(),
        name="packaged-workbasket-queue-confirm-create",
    ),
    path(
        url_prefix + "",
        RedirectView.as_view(pattern_name="packaged-workbasket-queue-ui-list"),
    ),
    path(
        url_prefix + "packaging-queue/",
        views.PackagedWorkbasketQueueView.as_view(),
        name="packaged-workbasket-queue-ui-list",
    ),
    path(
        url_prefix + "envelope-queue/",
        views.EnvelopeQueueView.as_view(),
        name="envelope-queue-ui-list",
    ),
]
