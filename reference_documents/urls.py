from django.urls import path
from rest_framework import routers

from reference_documents.views.alignment_report_views import AlignmentReportsDetailsView
from reference_documents.views.alignment_report_views import (
    ReferenceDocumentVersionAlignmentReportsDetailsView,
)
from reference_documents.views.example_views import ExampleReferenceDocumentsDetailView
from reference_documents.views.example_views import ExampleReferenceDocumentsListView
from reference_documents.views.preferential_quota_order_number_views import (
    PreferentialQuotaOrderNumberCreateView,
)
from reference_documents.views.preferential_quota_order_number_views import (
    PreferentialQuotaOrderNumberDeleteView,
)
from reference_documents.views.preferential_quota_order_number_views import (
    PreferentialQuotaOrderNumberEditView,
)
from reference_documents.views.preferential_quota_views import (
    PreferentialQuotaBulkCreateView,
)
from reference_documents.views.preferential_quota_views import (
    PreferentialQuotaCreateView,
)
from reference_documents.views.preferential_quota_views import (
    PreferentialQuotaDeleteView,
)
from reference_documents.views.preferential_quota_views import PreferentialQuotaEditView
from reference_documents.views.preferential_rate_views import PreferentialRateCreateView
from reference_documents.views.preferential_rate_views import PreferentialRateDeleteView
from reference_documents.views.preferential_rate_views import PreferentialRateEditView
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionConfirmCreate,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionConfirmDelete,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionConfirmUpdate,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionCreate,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionDelete,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionDetails,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionEdit,
)
from reference_documents.views.reference_document_views import (
    ReferenceDocumentConfirmCreate,
)
from reference_documents.views.reference_document_views import (
    ReferenceDocumentConfirmDelete,
)
from reference_documents.views.reference_document_views import (
    ReferenceDocumentConfirmUpdate,
)
from reference_documents.views.reference_document_views import ReferenceDocumentCreate
from reference_documents.views.reference_document_views import ReferenceDocumentDelete
from reference_documents.views.reference_document_views import ReferenceDocumentDetails
from reference_documents.views.reference_document_views import ReferenceDocumentList
from reference_documents.views.reference_document_views import ReferenceDocumentUpdate

app_name = "reference_documents"

api_router = routers.DefaultRouter()

detail = "<sid:sid>"
urlpatterns = [
    # Example views
    path(
        "reference-documents-example/",
        ExampleReferenceDocumentsListView.as_view(),
        name="example-ui-index",
    ),
    path(
        f"reference-documents-example-albania/",
        ExampleReferenceDocumentsDetailView.as_view(),
        name="example-ui-details",
    ),
    # Reference document views
    path(
        "reference_documents/",
        ReferenceDocumentList.as_view(),
        name="index",
    ),
    path(
        "reference_documents/create/",
        ReferenceDocumentCreate.as_view(),
        name="create",
    ),
    path(
        "reference_documents/<pk>/",
        ReferenceDocumentDetails.as_view(),
        name="details",
    ),
    path(
        "reference_documents/<pk>/update/",
        ReferenceDocumentUpdate.as_view(),
        name="update",
    ),
    path(
        f"<pk>/confirm-create/",
        ReferenceDocumentConfirmCreate.as_view(),
        name="confirm-create",
    ),
    path(
        f"reference_documents/<pk>/confirm-update/",
        ReferenceDocumentConfirmUpdate.as_view(),
        name="confirm-update",
    ),
    path(
        f"reference_documents/<pk>/delete/",
        ReferenceDocumentDelete.as_view(),
        name="delete",
    ),
    path(
        f"reference_documents/<deleted_pk>/confirm-delete/",
        ReferenceDocumentConfirmDelete.as_view(),
        name="confirm-delete",
    ),
    # reference document version views
    path(
        "reference_documents_versions/<pk>/",
        ReferenceDocumentVersionDetails.as_view(),
        name="version-details",
    ),
    path(
        "reference_documents_versions/<pk>/create",
        ReferenceDocumentVersionCreate.as_view(),
        name="version-create",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/edit/",
        ReferenceDocumentVersionEdit.as_view(),
        name="version-edit",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/version-delete/",
        ReferenceDocumentVersionDelete.as_view(),
        name="version-delete",
    ),
    path(
        "reference_document_versions/<pk>/confirm-update/",
        ReferenceDocumentVersionConfirmUpdate.as_view(),
        name="version-confirm-update",
    ),
    path(
        "reference_document_versions/<pk>/confirm-create/",
        ReferenceDocumentVersionConfirmCreate.as_view(),
        name="version-confirm-create",
    ),
    path(
        "reference_document_versions/<deleted_pk>/confirm-delete/",
        ReferenceDocumentVersionConfirmDelete.as_view(),
        name="version-confirm-delete",
    ),
    # Alignment report views
    path(
        "reference_document_version_alignment_reports/<pk>/",
        ReferenceDocumentVersionAlignmentReportsDetailsView.as_view(),
        name="version_alignment_reports",
    ),
    path(
        "alignment_reports/<pk>/",
        AlignmentReportsDetailsView.as_view(),
        name="alignment_reports",
    ),
    # Preferential Quotas
    path(
        "preferential_quotas/delete/<pk>/",
        PreferentialQuotaDeleteView.as_view(),
        name="preferential_quotas_delete",
    ),
    path(
        "preferential_quotas/edit/<pk>/",
        PreferentialQuotaEditView.as_view(),
        name="preferential_quotas_edit",
    ),
    path(
        "preferential_quota_order_numbers/<pk>/create_preferential_quotas/",
        PreferentialQuotaCreateView.as_view(),
        name="preferential_quotas_create",
    ),
    path(
        "reference_document_versions/<pk>/bulk_create_preferential_quotas/",
        PreferentialQuotaBulkCreateView.as_view(),
        name="preferential_quotas_bulk_create",
    ),
    # Preferential Rates
    path(
        "preferential_rates/delete/<pk>/",
        PreferentialRateDeleteView.as_view(),
        name="preferential_rates_delete",
    ),
    path(
        "preferential_rates/edit/<pk>/",
        PreferentialRateEditView.as_view(),
        name="preferential_rates_edit",
    ),
    path(
        "reference_document_versions/<pk>/create_preferential_rates/",
        PreferentialRateCreateView.as_view(),
        name="preferential_rates_create",
    ),
    # Preferential rate Quota order number
    path(
        "preferential_quota_order_numbers/delete/<pk>/",
        PreferentialQuotaOrderNumberDeleteView.as_view(),
        name="preferential_quota_order_number_delete",
    ),
    path(
        "preferential_quota_order_numbers/edit/<pk>/",
        PreferentialQuotaOrderNumberEditView.as_view(),
        name="preferential_quota_order_number_edit",
    ),
    path(
        "reference_document_versions/<pk>/create_preferential_quota_order_number/",
        PreferentialQuotaOrderNumberCreateView.as_view(),
        name="preferential_quota_order_number_create",
    ),
]
