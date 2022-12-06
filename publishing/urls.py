from django.urls import path
from django.views.generic.base import RedirectView

from publishing import views

url_prefix = "publishing/"

urlpatterns = [
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
