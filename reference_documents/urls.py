from django.urls import path
from rest_framework import routers

from reference_documents.views import alignment_report_views
from reference_documents.views import example_views
from reference_documents.views import preferential_quotas
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
        "reference_documents/create/",
        reference_document_views.ReferenceDocumentCreate.as_view(),
        name="create",
    ),
    path(
        "reference_documents/<pk>/",
        reference_document_views.ReferenceDocumentDetails.as_view(),
        name="details",
    ),
    path(
        "reference_documents/<pk>/update/",
        reference_document_views.ReferenceDocumentUpdate.as_view(),
        name="update",
    ),
    path(
        f"<pk>/confirm-create/",
        reference_document_views.ReferenceDocumentConfirmCreate.as_view(),
        name="confirm-create",
    ),
    path(
        f"<pk>/confirm-update/",
        reference_document_views.ReferenceDocumentConfirmUpdate.as_view(),
        name="confirm-update",
    ),
    path(
        f"<pk>/delete/",
        reference_document_views.ReferenceDocumentDelete.as_view(),
        name="delete",
    ),
    path(
        f"<deleted_pk>/confirm-delete/",
        reference_document_views.ReferenceDocumentConfirmDelete.as_view(),
        name="confirm-delete",
    ),
    # reference document version views
    path(
        "reference_document_versions/<pk>/",
        reference_document_version_views.ReferenceDocumentVersionDetails.as_view(),
        name="version_details",
    ),
    path(
        "reference_document_versions/edit/<pk>/",
        reference_document_version_views.ReferenceDocumentVersionEditView.as_view(),
        name="reference_document_version_edit",
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
    # Preferential Quotas
    path(
        "preferential_quotas/delete/<pk>/",
        preferential_quotas.PreferentialQuotaDeleteView.as_view(),
        name="preferential_quotas_delete",
    ),
    path(
        "preferential_quotas/edit/<pk>/",
        preferential_quotas.PreferentialQuotaEditView.as_view(),
        name="preferential_quotas_edit",
    ),
]
