from django.urls import path
from rest_framework import routers

import reference_documents.views as views

app_name = "reference_documents"

api_router = routers.DefaultRouter()

urlpatterns = [
    path(
        "reference_documents/",
        views.ReferenceDocumentList.as_view(),
        name="index",
    ),
    path(
        "reference_documents/<pk>/",
        views.ReferenceDocumentDetails.as_view(),
        name="details",
    ),
    path(
        "reference_document_versions/<pk>/",
        views.ReferenceDocumentVersionDetails.as_view(),
        name="version_details",
    ),
    path(
        "reference_document_version_alignment_reports/<pk>/",
        views.ReferenceDocumentVersionAlignmentReportsDetailsView.as_view(),
        name="reference_document_version_alignment_reports",
    ),
    path(
        "alignment_reports/<pk>/",
        views.AlignmentReportsDetailsView.as_view(),
        name="alignment_reports",
    ),
]
