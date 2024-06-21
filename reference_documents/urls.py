from django.urls import path
from rest_framework import routers

from reference_documents.views.alignment_report_views import AlignmentReportDetails
from reference_documents.views.order_number_views import (
    RefOrderNumberCreate,
)
from reference_documents.views.order_number_views import (
    RefOrderNumberDelete,
)
from reference_documents.views.order_number_views import (
    RefOrderNumberEdit,
)
from reference_documents.views.quota_suspension_range_views import RefQuotaSuspensionRangeCreate, RefQuotaSuspensionRangeEdit, RefQuotaSuspensionRangeDelete
from reference_documents.views.quota_suspension_views import RefQuotaSuspensionDelete, RefQuotaSuspensionEdit, RefQuotaSuspensionCreate
from reference_documents.views.quota_definition_range_views import RefQuotaDefinitionRangeDelete, RefQuotaDefinitionRangeCreate, RefQuotaDefinitionRangeEdit
from reference_documents.views.quota_definition_views import (
    RefQuotaDefinitionBulkCreate,
)
from reference_documents.views.quota_definition_views import RefQuotaDefinitionCreate
from reference_documents.views.quota_definition_views import RefQuotaDefinitionDelete
from reference_documents.views.quota_definition_views import RefQuotaDefinitionEdit
from reference_documents.views.rate_views import RefRateBulkCreate
from reference_documents.views.rate_views import RefRateCreate
from reference_documents.views.rate_views import RefRateDelete
from reference_documents.views.rate_views import RefRateEdit
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionChangeStateToEditable, ReferenceDocumentVersionAlignmentCheckQueued,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionChangeStateToInReview,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionChangeStateToPublished,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionAlignmentCheck,
)
from reference_documents.views.reference_document_version_views import (
    ReferenceDocumentVersionCheckResults,
)
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
from reference_documents.views.reference_document_views import ReferenceDocumentEdit
from reference_documents.views.reference_document_views import ReferenceDocumentList

app_name = "reference_documents"

api_router = routers.DefaultRouter()

detail = "<sid:sid>"
urlpatterns = [
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
        "reference_documents/<pk>/edit/",
        ReferenceDocumentEdit.as_view(),
        name="edit",
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
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_in_review/",
        ReferenceDocumentVersionChangeStateToInReview.as_view(),
        name="version-status-change-to-in-review",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_published/",
        ReferenceDocumentVersionChangeStateToPublished.as_view(),
        name="version-status-change-to-published",
    ),
    path(
        "reference_documents_versions/<ref_doc_pk>/version/<pk>/to_editable/",
        ReferenceDocumentVersionChangeStateToEditable.as_view(),
        name="version-status-change-to-editing",
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

    path(
        "reference_document_versions/<pk>/alignment-check-queued/",
        ReferenceDocumentVersionAlignmentCheckQueued.as_view(),
        name="alignment-check-queued",
    ),
    path(
        "reference_document_versions/<pk>/check-results/",
        ReferenceDocumentVersionCheckResults.as_view(),
        name="version-check-results",
    ),
    # Preferential Quotas
    path(
        "preferential_quotas/delete/<pk>/<version_pk>/",
        RefQuotaDefinitionDelete.as_view(),
        name="quota-definition-delete",
    ),
    path(
        "preferential_quotas/edit/<pk>/",
        RefQuotaDefinitionEdit.as_view(),
        name="quota-definition-edit",
    ),
    path(
        "order_numbers/<version_pk>/create_preferential_quotas/",
        RefQuotaDefinitionCreate.as_view(),
        name="quota-definition-create",
    ),
    path(
        "order_numbers/<version_pk>/create_quota_definition/<order_pk>/",
        RefQuotaDefinitionCreate.as_view(),
        name="quota-definition-create-for-order",
    ),
    path(
        "reference_document_versions/<pk>/bulk_create_quota_definitions/",
        RefQuotaDefinitionBulkCreate.as_view(),
        name="quota-definition-bulk-create",
    ),
    path(
        "reference_document_versions/<pk>/bulk_create_quota_definitions/<order_pk>/",
        RefQuotaDefinitionBulkCreate.as_view(),
        name="quota-definition-bulk-create-for-order",
    ),
    # Preferential Rates
    path(
        "preferential_rates/delete/<pk>/",
        RefRateDelete.as_view(),
        name="rate-delete",
    ),
    path(
        "preferential_rates/edit/<pk>/",
        RefRateEdit.as_view(),
        name="rate-edit",
    ),
    path(
        "reference_document_versions/<version_pk>/create_rate/",
        RefRateCreate.as_view(),
        name="rate-create",
    ),
    path(
        "reference_document_versions/<pk>/bulk_create_rates/",
        RefRateBulkCreate.as_view(),
        name="rates-bulk-create",
    ),
    # Preferential rate Quota order number
    path(
        "order_numbers/delete/<pk>/<version_pk>/",
        RefOrderNumberDelete.as_view(),
        name="order-number-delete",
    ),
    path(
        "order_numbers/edit/<pk>/",
        RefOrderNumberEdit.as_view(),
        name="order-number-edit",
    ),
    path(
        "reference_document_versions/<pk>/create_order_number/",
        RefOrderNumberCreate.as_view(),
        name="order-number-create",
    ),
    #  quota_definition_range
    path(
        "quota_definition_range/delete/<pk>/<version_pk>/",
        RefQuotaDefinitionRangeDelete.as_view(),
        name="quota-definition-range-delete",
    ),
    path(
        "quota_definition_range/edit/<pk>/",
        RefQuotaDefinitionRangeEdit.as_view(),
        name="quota-definition-range-edit",
    ),
    path(
        "order_numbers/<version_pk>/create_quota_definition_range/",
        RefQuotaDefinitionRangeCreate.as_view(),
        name="quota-definition-range-create",
    ),
    # preferential quota suspensions
    path(
        "quota_suspensions/delete/<pk>/<version_pk>/",
        RefQuotaSuspensionDelete.as_view(),
        name="quota-suspension-delete",
    ),
    path(
        "quota_suspensions/edit/<pk>/",
        RefQuotaSuspensionEdit.as_view(),
        name="quota-suspension-edit",
    ),
    path(
        "order_numbers/<version_pk>/create_quota_suspension/",
        RefQuotaSuspensionCreate.as_view(),
        name="quota-suspension-create",
    ),
    # preferential quota suspension templates
    path(
        "quota_suspension_range/delete/<pk>/<version_pk>/",
        RefQuotaSuspensionRangeDelete.as_view(),
        name="quota-suspension-range-delete",
    ),
    path(
        "quota_suspension_range/edit/<pk>/",
        RefQuotaSuspensionRangeEdit.as_view(),
        name="quota-suspension-range-edit",
    ),
    path(
        "quota_suspension_range/<version_pk>/create_quota_suspension_range/",
        RefQuotaSuspensionRangeCreate.as_view(),
        name="quota-suspension-range-create",
    ),
    # alignment checks
    path(
        "reference_document_versions/<pk>/alignment-reports/",
        ReferenceDocumentVersionAlignmentCheck.as_view(),
        name="alignment-reports",
    ),
    path(
        "reference_document_versions/<version_pk>/alignment-reports/<pk>/",
        AlignmentReportDetails.as_view(),
        name="alignment-report-details",
    ),
]
