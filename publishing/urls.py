from django.urls import include
from django.urls import path
from django.views.generic.base import RedirectView

from publishing import views

app_name = "publishing"

ui_patterns = [
    path(
        "",
        RedirectView.as_view(
            pattern_name="publishing:packaged-workbasket-queue-ui-list",
        ),
    ),
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
        "packaging-queue/",
        views.PackagedWorkbasketQueueView.as_view(),
        name="packaged-workbasket-queue-ui-list",
    ),
    path(
        "envelope-queue/",
        views.EnvelopeQueueView.as_view(),
        name="envelope-queue-ui-list",
    ),
    path(
        "download-queued-envelope/<pk>/",
        views.DownloadQueuedEnvelopeView.as_view(),
        name="download-queued-envelope-ui-download",
    ),
    path(
        "download-admin-envelope/<pk>/",
        views.DownloadAdminEnvelopeView.as_view(),
        name="admin-envelope-ui-download",
    ),
    path(
        "envelope-queue/accept/<pk>/",
        views.AcceptEnvelopeView.as_view(),
        name="accept-envelope-ui-detail",
    ),
    path(
        "envelope-queue/accept-confirm/<pk>/",
        views.AcceptEnvelopeConfirmView.as_view(),
        name="accept-envelope-confirm-ui-detail",
    ),
    path(
        "envelope-queue/reject/<pk>/",
        views.RejectEnvelopeView.as_view(),
        name="reject-envelope-ui-detail",
    ),
    path(
        "envelope-queue/reject-confirm/<pk>/",
        views.RejectEnvelopeConfirmView.as_view(),
        name="reject-envelope-confirm-ui-detail",
    ),
    path(
        "download-admin-loading-report/<pk>/",
        views.DownloadAdminLoadingReportView.as_view(),
        name="admin-loading-report-ui-download",
    ),
    path(
        "envelope-list/",
        views.EnvelopeListView.as_view(),
        name="envelope-list-ui-list",
    ),
    path(
        "envelope-file-history/<pk>/",
        views.EnvelopeFileHistoryView.as_view(),
        name="envelope-file-history-ui-detail",
    ),
]


urlpatterns = [
    path("publishing/", include(ui_patterns)),
]
