from django.urls import path
from rest_framework import routers

from reference_documents.views import alignment_report_views
from reference_documents.views import example_views
from reference_documents.views import preferential_quotas
from reference_documents.views import preferential_rates
from reference_documents.views import reference_document_version_views
from reference_documents.views import reference_document_views

app_name = "reference_documents"

api_router = routers.DefaultRouter()

detail = "<sid:sid>"
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
        f"reference_documents/<pk>/confirm-update/",
        reference_document_views.ReferenceDocumentConfirmUpdate.as_view(),
        name="confirm-update",
    ),
    path(
        f"reference_documents/<pk>/delete/",
        reference_document_views.ReferenceDocumentDelete.as_view(),
        name="delete",
    ),
    path(
        f"reference_documents/<deleted_pk>/confirm-delete/",
        reference_document_views.ReferenceDocumentConfirmDelete.as_view(),
        name="confirm-delete",
    ),
    # reference document version views
    path(
        "reference_documents_versions/<pk>/",
        reference_document_version_views.ReferenceDocumentVersionDetails.as_view(),
        name="version-details",
    ),
    path(
        "reference_documents_versions/<pk>/create",
        reference_document_version_views.ReferenceDocumentVersionCreate.as_view(),
        name="version-create",
    ),
    path(
        "reference_documents_versions/<pk>/version/<version_pk>/edit/",
        reference_document_version_views.ReferenceDocumentVersionEdit.as_view(),
        name="version-edit",
    ),
    path(
        "reference_documents_versions/<pk>/version/<version_pk>/version-delete/",
        reference_document_version_views.ReferenceDocumentVersionDelete.as_view(),
        name="version-delete",
    ),
    path(
        "reference_document_versions/<pk>/confirm-update/",
        reference_document_version_views.ReferenceDocumentVersionConfirmUpdate.as_view(),
        name="version-confirm-update",
    ),
    path(
        "reference_document_versions/<pk>/confirm-create/",
        reference_document_version_views.ReferenceDocumentVersionConfirmCreate.as_view(),
        name="version-confirm-create",
    ),
    path(
        "reference_document_versions/<deleted_pk>/confirm-delete/",
        reference_document_version_views.ReferenceDocumentVersionConfirmDelete.as_view(),
        name="version-confirm-delete",
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
    path(
        "reference_document_versions/<pk>/create_preferential_quotas/",
        preferential_quotas.PreferentialQuotaCreateView.as_view(),
        name="preferential_quotas_create",
    ),
    # Preferential Rates
    path(
        "preferential_rates/delete/<pk>/",
        preferential_rates.PreferentialRateDeleteView.as_view(),
        name="preferential_rates_delete",
    ),
    path(
        "preferential_rates/edit/<pk>/",
        preferential_rates.PreferentialRateEditView.as_view(),
        name="preferential_rates_edit",
    ),
    path(
        "reference_document_versions/<pk>/create_preferential_rates/",
        preferential_rates.PreferentialRateCreateView.as_view(),
        name="preferential_rates_create",
    ),
]
