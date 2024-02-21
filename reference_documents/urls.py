from django.urls import path
from rest_framework import routers

from reference_documents.views import alignment_report_views
from reference_documents.views import example_views
from reference_documents.views import reference_document_version_views
from reference_documents.views import reference_document_views

app_name = "reference_documents"

api_router = routers.DefaultRouter()

urlpatterns = [
    # Example views
    path(
        "reference-documents-example/",
        example_views.ReferenceDocumentsListView.as_view(),
        name="example-ui-index",
    ),
    path(
        f"reference-documents-example-albania/",
        example_views.ReferenceDocumentsDetailView.as_view(),
        name="example-ui-details",
    ),
    # Reference document views
    path(
        "reference_documents/",
        reference_document_views.ReferenceDocumentList.as_view(),
        name="index",
    ),
    path(
        "reference_documents/<pk>/",
        reference_document_views.ReferenceDocumentDetails.as_view(),
        name="details",
    ),
    # reference document version views
    path(
        "reference_document_versions/<pk>/",
        reference_document_version_views.ReferenceDocumentVersionDetails.as_view(),
        name="version_details",
    ),
    # Alignment report views
    path(
        "reference_document_version_alignment_reports/<pk>/",
        alignment_report_views.ReferenceDocumentVersionAlignmentReportsDetailsView.as_view(),
        name="version_alignment_reports",
    ),
    path(
        "alignment_reports/<pk>/",
        alignment_report_views.AlignmentReportsDetailsView.as_view(),
        name="alignment_reports",
    ),
]
